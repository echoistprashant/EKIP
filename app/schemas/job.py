import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.document import DocumentResponse


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    stage: str
    progress: int
    chunk_count: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    job: IngestionJobResponse | None = None
    chunk_count: int = 0
