from collections.abc import AsyncIterator
import json
import time
import httpx
from fastapi import HTTPException

from app.llm.client import LLMRequest, LLMResult, StreamChunk, TokenUsage
from app.llm.cost import calculate_cost_usd


class GeminiLLMClient:
    """
    Google Gemini REST client supporting free-tier API keys.
    Converts universal ChatMessage format to Gemini Content objects.
    Supports both generate() and stream() via Server-Sent Events (alt=sse).
    """

    def __init__(self, api_key: str, default_model: str = "gemini-flash-lite-latest", timeout_seconds: float = 30.0):
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout_seconds

    def _build_payload(self, req: LLMRequest) -> tuple[str, dict]:
        model = req.model or self.default_model
        contents = []
        system_instruction = None

        for msg in req.messages:
            if msg.role == "system":
                system_instruction = {"parts": [{"text": msg.content}]}
            else:
                role = "model" if msg.role == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": req.temperature,
                "maxOutputTokens": req.max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        return model, payload

    async def generate(self, req: LLMRequest) -> LLMResult:
        model, payload = self._build_payload(req)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        start_time = time.monotonic()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
            except httpx.TimeoutException as e:
                err = HTTPException(status_code=504, detail=f"Gemini API timed out after {self.timeout}s")
                err.status_code = 504
                raise err from e
            except httpx.RequestError as e:
                err = HTTPException(status_code=503, detail=f"Network error connecting to Gemini API: {e}")
                err.status_code = 503
                raise err from e

        if response.status_code != 200:
            err = HTTPException(status_code=response.status_code, detail=f"Gemini API returned error: {response.text}")
            err.status_code = response.status_code
            raise err

        data = response.json()
        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Extract generated text
        candidates = data.get("candidates", [])
        if not candidates or "content" not in candidates[0]:
            content_text = ""
            finish_reason = "empty"
        else:
            parts = candidates[0]["content"].get("parts", [])
            content_text = parts[0].get("text", "") if parts else ""
            finish_reason = candidates[0].get("finishReason", "stop").lower()

        # Extract usage metadata
        usage_meta = data.get("usageMetadata", {})
        prompt_tokens = usage_meta.get("promptTokenCount", 0)
        completion_tokens = usage_meta.get("candidatesTokenCount", 0)

        cost = calculate_cost_usd(model, prompt_tokens, completion_tokens)

        return LLMResult(
            content=content_text,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            model=model,
            latency_ms=latency_ms,
            cost_usd=cost,
            finish_reason=finish_reason,
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamChunk]:
        model, payload = self._build_payload(req)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    err_text = await response.aread()
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Gemini API streaming error: {err_text.decode('utf-8', errors='ignore')}",
                    )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if not data_str:
                            continue
                        try:
                            chunk_data = json.loads(data_str)
                            candidates = chunk_data.get("candidates", [])
                            if candidates and "content" in candidates[0]:
                                parts = candidates[0]["content"].get("parts", [])
                                for p in parts:
                                    text_part = p.get("text", "")
                                    if text_part:
                                        yield StreamChunk(text=text_part)
                        except Exception:
                            continue

        yield StreamChunk(text="", finish_reason="stop")
