import pytest

from app.llm.client import ChatMessage, LLMRequest, StreamChunk
from app.llm.providers.mock_llm import MockLLMClient
from app.llm.router import ResilientLLMRouter
from app.services.streaming_service import sse_event


class TestMockLLMStreaming:
    @pytest.mark.asyncio
    async def test_mock_llm_stream_chunks(self):
        client = MockLLMClient(default_response="Alpha Beta Gamma [1]")
        req = LLMRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="mock-model",
        )

        tokens = []
        finish_chunk = None

        async for chunk in client.stream(req):
            if chunk.text:
                tokens.append(chunk.text)
            if chunk.finish_reason:
                finish_chunk = chunk

        assert len(tokens) >= 3
        assert "".join(tokens) == "Alpha Beta Gamma [1]"
        assert finish_chunk is not None
        assert finish_chunk.finish_reason == "stop"
        assert finish_chunk.usage is not None
        assert finish_chunk.usage.total_tokens > 0


class TestResilientRouterStreaming:
    @pytest.mark.asyncio
    async def test_streaming_fallback_on_primary_failure(self):
        primary = MockLLMClient()
        primary.simulate_failure(RuntimeError("Primary model stream interrupted"))

        fallback = MockLLMClient(default_response="Fallback stream active")

        router = ResilientLLMRouter(
            primary_client=primary,
            primary_model="primary-mock",
            fallback_client=fallback,
            fallback_model="fallback-mock",
        )

        req = LLMRequest(
            messages=[ChatMessage(role="user", content="Test")],
            model="primary-mock",
        )

        tokens = []
        async for chunk in router.stream(req):
            if chunk.text:
                tokens.append(chunk.text)

        assert "".join(tokens) == "Fallback stream active"


class TestSSEFormatter:
    def test_sse_event_formatting(self):
        formatted = sse_event("token", {"text": "hello"})
        assert formatted.startswith("event: token\n")
        assert 'data: {"text": "hello"}\n\n' in formatted
