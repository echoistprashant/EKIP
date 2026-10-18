from functools import lru_cache

from app.core.config import settings
from app.llm.client import ChatMessage, LLMClient, LLMRequest, LLMResult, StreamChunk, TokenUsage
from app.llm.providers.gemini_llm import GeminiLLMClient
from app.llm.providers.mock_llm import MockLLMClient
from app.llm.router import ResilientLLMRouter


@lru_cache
def get_llm_client() -> LLMClient:
    """
    Factory function returning configured resilient LLM client.
    If Gemini API key is configured, sets up Gemini as primary with Mock fallback.
    Otherwise defaults to MockLLMClient for zero-cost local operations.
    """
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        primary = GeminiLLMClient(
            api_key=settings.GEMINI_API_KEY,
            default_model=settings.LLM_MODEL,
        )
        fallback = MockLLMClient()
        return ResilientLLMRouter(
            primary_client=primary,
            primary_model=settings.LLM_MODEL,
            fallback_client=fallback,
            fallback_model="mock-model",
        )

    return MockLLMClient()


__all__ = [
    "ChatMessage",
    "TokenUsage",
    "StreamChunk",
    "LLMRequest",
    "LLMResult",
    "LLMClient",
    "get_llm_client",
]
