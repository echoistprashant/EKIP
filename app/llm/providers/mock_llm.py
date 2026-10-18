import asyncio
from collections.abc import AsyncIterator
import time
from typing import Any

from app.llm.client import LLMRequest, LLMResult, StreamChunk, TokenUsage
from app.llm.cost import calculate_cost_usd


class MockLLMClient:
    """
    Deterministic Mock LLM client for tests and offline operation.
    Zero API cost, predictable output, with simulated latency and token usage.
    Supports both non-streaming generate() and streaming stream().
    """

    def __init__(self, default_response: str | None = None):
        self.default_response = default_response
        self.forced_exception: Exception | None = None
        self.call_count = 0

    def simulate_failure(self, exc: Exception | None):
        """Helper to test retry and circuit breaker logic."""
        self.forced_exception = exc

    def _generate_response_text(self, prompt_text: str) -> str:
        if self.default_response:
            return self.default_response
        if "<context>" in prompt_text and "</context>" in prompt_text:
            context_block = prompt_text.split("<context>")[-1].split("</context>")[0].strip()
            lines = [
                line.strip()
                for line in context_block.splitlines()
                if line.strip() and not line.strip().startswith("[") and not line.strip().startswith("Document:")
            ]
            if lines:
                return f"{lines[0].rstrip('.')} [1]."
        return "Based on the provided documentation, the requested procedure is fully verified [1]."

    async def generate(self, req: LLMRequest) -> LLMResult:
        self.call_count += 1

        if self.forced_exception is not None:
            raise self.forced_exception

        start = time.monotonic()

        # Compute synthetic tokens from message lengths
        prompt_text = "".join(m.content for m in req.messages)
        input_tokens = max(10, len(prompt_text.split()))

        response_text = self._generate_response_text(prompt_text)

        output_tokens = max(5, len(response_text.split()))
        latency_ms = int((time.monotonic() - start) * 1000)

        cost = calculate_cost_usd(req.model, input_tokens, output_tokens)

        return LLMResult(
            content=response_text,
            usage=TokenUsage(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
            model=req.model,
            latency_ms=latency_ms,
            cost_usd=cost,
            finish_reason="stop",
        )

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamChunk]:
        self.call_count += 1

        if self.forced_exception is not None:
            raise self.forced_exception

        prompt_text = "".join(m.content for m in req.messages)
        response_text = self._generate_response_text(prompt_text)

        words = response_text.split(" ")
        for idx, word in enumerate(words):
            token_str = word if idx == len(words) - 1 else word + " "
            yield StreamChunk(text=token_str)
            await asyncio.sleep(0)

        prompt_text = "".join(m.content for m in req.messages)
        input_tokens = max(10, len(prompt_text.split()))
        output_tokens = max(5, len(words))

        yield StreamChunk(
            text="",
            finish_reason="stop",
            usage=TokenUsage(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
        )
