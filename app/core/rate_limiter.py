import asyncio
import logging
import time
import uuid

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

RATE_LIMIT_LUA = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
if ttl < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
    ttl = tonumber(ARGV[1])
end
return {current, ttl}
"""


class RedisRateLimiter:
    """
    Fixed-window rate limiter powered by Redis with Lua atomicity.
    Falls back gracefully to local sliding-window memory store if Redis is unreachable.
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: aioredis.Redis | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None
        self._memory_store: dict[str, list[float]] = {}

    def _get_client(self) -> aioredis.Redis:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._client is not None and self._client_loop is not None and (self._client_loop.is_closed() or self._client_loop != current_loop):
            self._client = None

        if self._client is None:
            self._client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=2.0,
            )
            self._client_loop = current_loop
        return self._client

    async def check(
        self,
        key_prefix: str,
        identifier: str | uuid.UUID,
        max_requests: int,
        window_seconds: int = 60,
    ) -> None:
        """
        Check rate limit for a given entity.
        Raises HTTP 429 with 'Retry-After' response header when limit is exceeded.
        """
        key = f"ekip:ratelimit:{key_prefix}:{identifier}"
        try:
            client = self._get_client()
            res = await client.eval(RATE_LIMIT_LUA, 1, key, window_seconds)
            current_count = int(res[0])
            ttl = int(res[1])
            if current_count > max_requests:
                retry_after = max(ttl, 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit of {max_requests} requests per {window_seconds}s exceeded for {key_prefix}.",
                    headers={"Retry-After": str(retry_after)},
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.debug(f"Redis rate limiter fallback to in-memory: {e}")
            now = time.time()
            timestamps = self._memory_store.get(key, [])
            timestamps = [t for t in timestamps if now - t < window_seconds]
            if len(timestamps) >= max_requests:
                oldest = timestamps[0]
                retry_after = max(int(window_seconds - (now - oldest)), 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit of {max_requests} requests per {window_seconds}s exceeded for {key_prefix}.",
                    headers={"Retry-After": str(retry_after)},
                )
            timestamps.append(now)
            self._memory_store[key] = timestamps


limiter = RedisRateLimiter(settings.REDIS_URL)


async def rate_limit_query(current_user: User = Depends(get_current_user)) -> None:
    """Per-user rate limit for RAG query endpoints."""
    await limiter.check(
        key_prefix="user_query",
        identifier=str(current_user.id),
        max_requests=settings.RATE_LIMIT_QUERY_PER_MINUTE,
        window_seconds=60,
    )


async def rate_limit_upload(current_user: User = Depends(get_current_user)) -> None:
    """Per-tenant rate limit for file upload endpoints."""
    await limiter.check(
        key_prefix="tenant_upload",
        identifier=str(current_user.tenant_id),
        max_requests=settings.RATE_LIMIT_UPLOAD_PER_MINUTE,
        window_seconds=60,
    )
