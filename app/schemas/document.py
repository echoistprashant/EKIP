import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    collection_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., max_length=100)
    content_hash: str = Field(..., min_length=64, max_length=64)  # SHA-256
    storage_key: str = Field(..., max_length=1024)
    source_uri: str | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    collection_id: uuid.UUID
    title: str
    mime_type: str
    content_hash: str
    storage_key: str
    status: str
    current_version: int
    created_at: datetime
