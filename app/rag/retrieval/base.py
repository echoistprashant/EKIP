import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class AccessScope:
    """Encapsulates caller tenant, identity, and permitted collection perimeters."""
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    collection_ids: list[uuid.UUID] | None = None


@dataclass
class Candidate:
    """Represents a retrieved chunk with score and provenance metadata."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    collection_id: uuid.UUID
    content: str
    section_path: str
    page_start: int | None
    page_end: int | None
    score: float
    retrieval_method: str  # 'dense', 'lexical', or 'hybrid_rrf'
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseRetriever(Protocol):
    """Protocol for chunk retrieval backends."""
    async def retrieve(
        self,
        query: str,
        scope: AccessScope,
        top_k: int = 50,
    ) -> list[Candidate]:
        ...
