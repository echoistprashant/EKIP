import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenPayload(BaseModel):
    sub: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    exp: int


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    tenant_name: str | None = None
    invite_token: str | None = None


class InviteCreateRequest(BaseModel):
    role: Literal["viewer", "editor", "admin", "evaluator"] = "viewer"
    expires_hours: int = Field(default=48, ge=1, le=168)


class InviteResponse(BaseModel):
    invite_token: str
    tenant_id: uuid.UUID
    role: str
    expires_at: datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str
    is_active: bool
