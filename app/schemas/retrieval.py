import uuid
from pydantic import BaseModel, ConfigDict, Field


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    collection_ids: list[uuid.UUID] | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    rerank: bool = Field(default=False, description="Apply Cross-Encoder reranking")
    top_n: int = Field(default=5, ge=1, le=20, description="Number of candidates to return if rerank is True")


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    collection_id: uuid.UUID
    content: str
    section_path: str
    page_start: int | None
    page_end: int | None
    score: float
    retrieval_method: str


class RetrieveResponse(BaseModel):
    query: str
    count: int
    candidates: list[CandidateResponse]
