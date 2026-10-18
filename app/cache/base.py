from dataclasses import dataclass, field
from typing import Any, Protocol
import uuid

from app.schemas.query import QueryResponse


@dataclass
class CacheHit:
    """Represents a successful cache lookup."""
    response: QueryResponse
    cache_type: str  # "exact" or "semantic"
    similarity: float | None
    matched_query: str


def make_collection_fingerprint(collection_ids: list[uuid.UUID] | None) -> str:
    """Computes a deterministic hash fingerprint for the collection access perimeter."""
    if not collection_ids:
        return "all"
    return "_".join(sorted(str(cid) for cid in collection_ids))


def compute_cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """
    Computes cosine similarity between two unit-normalized vectors.
    Since embeddings from FastEmbed and MockEmbedder are L2 normalized (||v|| = 1.0),
    cosine similarity simplifies to the dot product.
    """
    if len(v1) != len(v2):
        return 0.0
    return sum(a * b for a, b in zip(v1, v2, strict=True))


class BaseSemanticCache(Protocol):
    """Protocol for semantic caching engines."""

    async def get(
        self,
        tenant_id: uuid.UUID,
        collection_ids: list[uuid.UUID] | None,
        query: str,
        query_embedding: list[float] | None = None,
    ) -> CacheHit | None:
        """Looks up exact hash match (L1) or vector similarity match (L2)."""
        ...

    async def set(
        self,
        tenant_id: uuid.UUID,
        collection_ids: list[uuid.UUID] | None,
        query: str,
        query_embedding: list[float] | None,
        response: QueryResponse,
        ttl_seconds: int = 86400,
    ) -> None:
        """Stores query response in both exact and semantic cache tiers."""
        ...

    async def invalidate_collection(
        self,
        tenant_id: uuid.UUID,
        collection_id: uuid.UUID,
    ) -> int:
        """Evicts cached entries associated with an updated collection."""
        ...

    async def clear(self) -> None:
        """Flushes cache."""
        ...
