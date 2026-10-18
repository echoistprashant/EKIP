from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ChatMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMRequest:
    messages: list[ChatMessage]
    model: str
    temperature: float = 0.0
    max_tokens: int = 1000
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResult:
    content: str
    usage: TokenUsage
    model: str
    latency_ms: int
    cost_usd: float = 0.0
    finish_reason: str = "stop"  # "stop", "length", "content_filter"


class LLMClient(Protocol):
    """Protocol for provider-agnostic LLM clients."""

    async def generate(self, req: LLMRequest) -> LLMResult:
        """Execute non-streaming completion with token and cost accounting."""
        ...
