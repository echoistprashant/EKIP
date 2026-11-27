import uuid
from fastapi import HTTPException
import pytest

from app.core.rate_limiter import RedisRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit():
    """Verify that requests under the limit succeed."""
    limiter = RedisRateLimiter("redis://localhost:6379/0")
    unique_user = str(uuid.uuid4())

    # 3 requests with limit of 5 should succeed
    for _ in range(3):
        await limiter.check("test_allow", unique_user, max_requests=5, window_seconds=60)


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit_with_retry_after():
    """Verify that requests exceeding limit raise 429 with Retry-After header."""
    limiter = RedisRateLimiter("redis://localhost:6379/0")
    unique_user = str(uuid.uuid4())

    # Limit = 3 requests
    for _ in range(3):
        await limiter.check("test_block", unique_user, max_requests=3, window_seconds=60)

    # 4th request must raise 429
    with pytest.raises(HTTPException) as exc:
        await limiter.check("test_block", unique_user, max_requests=3, window_seconds=60)

    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers
    retry_after = int(exc.value.headers["Retry-After"])
    assert 1 <= retry_after <= 60


@pytest.mark.asyncio
async def test_rate_limiter_in_memory_fallback():
    """Verify that if Redis fails or URL is invalid, fallback still enforces 429."""
    limiter = RedisRateLimiter("redis://nonexistent-host:9999/0")
    unique_user = str(uuid.uuid4())

    for _ in range(2):
        await limiter.check("test_fallback", unique_user, max_requests=2, window_seconds=10)

    # 3rd request should hit in-memory limit and raise 429
    with pytest.raises(HTTPException) as exc:
        await limiter.check("test_fallback", unique_user, max_requests=2, window_seconds=10)

    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers
