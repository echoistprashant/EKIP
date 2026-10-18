from collections.abc import AsyncIterator
import logging
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.client import LLMClient, LLMRequest, LLMResult, StreamChunk
from app.llm.retry import execute_with_retry

logger = logging.getLogger("ekip.llm.router")


class ResilientLLMRouter:
    """
    Manages primary and fallback LLM clients with Circuit Breakers and Retries.
    Guarantees graceful failover for both generate() and stream() requests.
    """

    def __init__(
        self,
        primary_client: LLMClient,
        primary_model: str,
        fallback_client: LLMClient | None = None,
        fallback_model: str | None = None,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ):
        self.primary_client = primary_client
        self.primary_model = primary_model
        self.fallback_client = fallback_client
        self.fallback_model = fallback_model or "mock-model"

        self.primary_breaker = CircuitBreaker(
            name="primary-llm",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    async def generate(self, req: LLMRequest) -> LLMResult:
        # Check if primary provider is healthy
        if self.primary_breaker.is_available():
            try:
                # Wrap primary call in exponential retry with jitter
                result = await execute_with_retry(
                    operation=lambda: self.primary_client.generate(req),
                    max_attempts=3,
                    base_delay=0.1,
                )
                self.primary_breaker.record_success()
                return result
            except Exception as e:
                self.primary_breaker.record_failure()
                logger.error(
                    f"Primary provider failed for model {req.model}: {e}. "
                    f"Circuit status: {self.primary_breaker.state.value}. Attempting fallback..."
                )

        # Fallback path if primary is open or failed
        if self.fallback_client is not None:
            logger.warning(f"Routing request to fallback client with model {self.fallback_model}")
            fallback_req = LLMRequest(
                messages=req.messages,
                model=self.fallback_model,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                metadata=req.metadata,
            )
            return await self.fallback_client.generate(fallback_req)

        raise RuntimeError("Primary LLM provider failed and no fallback client is configured.")

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamChunk]:
        # Check if primary provider is healthy
        if self.primary_breaker.is_available():
            try:
                async for chunk in self.primary_client.stream(req):
                    yield chunk
                self.primary_breaker.record_success()
                return
            except Exception as e:
                self.primary_breaker.record_failure()
                logger.error(f"Primary provider streaming failed: {e}. Falling back...")

        # Fallback streaming path
        if self.fallback_client is not None:
            fallback_req = LLMRequest(
                messages=req.messages,
                model=self.fallback_model,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                metadata=req.metadata,
            )
            async for chunk in self.fallback_client.stream(fallback_req):
                yield chunk
            return

        raise RuntimeError("Primary LLM provider failed and no fallback client is configured.")
