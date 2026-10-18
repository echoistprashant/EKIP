from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class QueryTransformationResult:
    """Holds transformed queries, hypothetical documents, and metadata."""
    original_query: str
    transformed_query: str
    expanded_queries: list[str] = field(default_factory=list)
    strategy_used: str = "none"  # "none", "hyde", "expansion", "rewrite"
    hypothetical_document: str | None = None


class BaseQueryTransformer(Protocol):
    """Protocol for Query Transformation implementations."""

    async def transform(self, query: str) -> QueryTransformationResult:
        ...
