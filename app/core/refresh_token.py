import asyncio
import json
import logging
import secrets
import uuid
from typing import Any
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RefreshTokenManager:
    """Manages refresh tokens stored in Redis with revocation and TTL enforcement."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: aioredis.Redis | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None
        self._fallback_store: dict[str, dict[str, Any]] = {}
        self._user_tokens_fallback: dict[str, set[str]] = {}

    def _get_client(self) -> aioredis.Redis:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._client is not None:
            if self._client_loop is not None and (self._client_loop.is_closed() or self._client_loop != current_loop):
                self._client = None

        if self._client is None:
            self._client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=2.0,
            )
            self._client_loop = current_loop
        return self._client

    async def create_refresh_token(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
        """Create a secure random refresh token and store in Redis."""
        token = secrets.token_urlsafe(48)
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        payload = {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
        }

        try:
            client = self._get_client()
            key = f"refresh_token:{token}"
            user_key = f"user_refresh_tokens:{user_id}"
            await client.set(key, json.dumps(payload), ex=ttl)
            await client.sadd(user_key, token)
            await client.expire(user_key, ttl)
        except Exception as e:
            logger.warning(f"Redis unavailable for refresh token creation, using fallback store: {e}")
            self._fallback_store[token] = payload
            if str(user_id) not in self._user_tokens_fallback:
                self._user_tokens_fallback[str(user_id)] = set()
            self._user_tokens_fallback[str(user_id)].add(token)

        return token

    async def get_and_validate_token(self, token: str) -> dict[str, Any] | None:
        """Validate token exists and has not been revoked."""
        if not token:
            return None

        try:
            client = self._get_client()
            raw = await client.get(f"refresh_token:{token}")
            if raw is None:
                return self._fallback_store.get(token)
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Redis get failed, checking fallback store: {e}")
            return self._fallback_store.get(token)

    async def revoke_refresh_token(self, token: str) -> bool:
        """Revoke a single refresh token."""
        if not token:
            return False

        revoked = False
        try:
            client = self._get_client()
            key = f"refresh_token:{token}"
            raw = await client.get(key)
            if raw:
                try:
                    data = json.loads(raw)
                    user_id = data.get("user_id")
                    if user_id:
                        await client.srem(f"user_refresh_tokens:{user_id}", token)
                except Exception:
                    pass
            deleted = await client.delete(key)
            revoked = bool(deleted)
        except Exception as e:
            logger.warning(f"Redis revoke failed, checking fallback store: {e}")

        if token in self._fallback_store:
            data = self._fallback_store.pop(token)
            uid = data.get("user_id")
            if uid and uid in self._user_tokens_fallback:
                self._user_tokens_fallback[uid].discard(token)
            revoked = True

        return revoked

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> int:
        """Revoke all refresh tokens for a user (e.g. on logout)."""
        count = 0
        try:
            client = self._get_client()
            user_key = f"user_refresh_tokens:{user_id}"
            tokens = await client.smembers(user_key)
            for t in tokens:
                await client.delete(f"refresh_token:{t}")
                count += 1
            await client.delete(user_key)
        except Exception as e:
            logger.warning(f"Redis revoke all failed, checking fallback store: {e}")

        uid_str = str(user_id)
        tokens = self._user_tokens_fallback.pop(uid_str, set())
        for t in tokens:
            self._fallback_store.pop(t, None)
            count += 1

        return count


_global_token_manager: RefreshTokenManager | None = None


def get_refresh_token_manager() -> RefreshTokenManager:
    global _global_token_manager
    if _global_token_manager is None:
        _global_token_manager = RefreshTokenManager(redis_url=settings.REDIS_URL)
    return _global_token_manager
