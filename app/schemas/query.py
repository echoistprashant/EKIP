import uuid
from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="The user query or question.")
    collection_ids: list[uuid.UUID] | None = Field(
        default=None, description="Optional collection IDs to scope retrieval."
    )
    top_k: int = Field(default=15, ge=1, le=50, description="Max raw candidates to retrieve in Stage 1.")
    rerank: bool = Field(default=True, description="Whether to apply Stage 2 Cross-Encoder reranking.")
    top_n: int = Field(default=5, ge=1, le=20, description="Number of candidates to keep after reranking.")
    compress_context: bool = Field(default=True, description="Whether to apply extractive sentence compression.")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="LLM sampling temperature.")
    max_context_tokens: int = Field(
        default=3000, ge=500, le=16000, description="Token budget for context injection."
    )


class CitationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: int = Field(..., description="1-indexed source number referenced in text as [n].")
    chunk_id: uuid.UUID = Field(..., description="Underlying database Chunk UUID.")
    document_id: uuid.UUID = Field(..., description="Parent Document UUID.")
    section_path: str = Field(..., description="Hierarchical heading path of the source chunk.")
    page_start: int | None = Field(default=None, description="Starting page number if applicable.")
    page_end: int | None = Field(default=None, description="Ending page number if applicable.")
    snippet: str = Field(..., description="Truncated preview of the chunk content.")
    relevance_score: float = Field(..., description="Fused retrieval/rerank score.")


class QueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: str
    answer: str
    citations: list[CitationItem]
    abstained: bool
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    query_id: uuid.UUID | None = None
