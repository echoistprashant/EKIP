import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def get_password_hash(password: str) -> str:
    """Hash plaintext password with bcrypt and unique salt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def create_access_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str,
    expires_delta: timedelta | None = None
) -> str:
    """
    Generate signed JWT containing user_id, tenant_id, and role.
    Signature prevents client tampering.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify JWT signature and expiry.
    Raises jwt.PyJWTError if invalid or expired.
    """
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") == "invite":
        raise jwt.PyJWTError("Invite token cannot be used as an access token")
    return payload


def create_invite_token(
    tenant_id: uuid.UUID,
    role: str,
    expires_delta: timedelta | None = None
) -> str:
    """
    Generate signed JWT invite token for joining a tenant with a pre-assigned role.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=48)

    payload: dict[str, Any] = {
        "sub": "invite",
        "type": "invite",
        "tenant_id": str(tenant_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_invite_token(token: str) -> dict[str, Any]:
    """
    Decode and verify invite token signature and claims.
    Raises jwt.PyJWTError if invalid, expired, or wrong type.
    """
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "invite":
        raise jwt.PyJWTError("Token is not an invite token")
    if not payload.get("tenant_id") or not payload.get("role"):
        raise jwt.PyJWTError("Invite token missing required claims")
    return payload

