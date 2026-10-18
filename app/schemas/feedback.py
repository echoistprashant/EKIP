import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    query_id: uuid.UUID
    is_helpful: bool
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)
    feedback_type: str = Field(
        default="general",
        pattern=r"^(general|hallucination|missing_info|unhelpful|incorrect_citation|other)$",
    )


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    query_id: uuid.UUID
    is_helpful: bool
    rating: int | None
    comment: str | None
    feedback_type: str
    created_at: datetime
