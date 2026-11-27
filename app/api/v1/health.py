from fastapi import APIRouter, Depends, Response, status
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Deep health check verifying connectivity to core dependencies:
    - Runs 'SELECT 1' against PostgreSQL
    - Runs 'PING' against Redis
    Returns HTTP 503 if either dependency fails.
    """
    db_status = "unknown"
    redis_status = "unknown"
    is_healthy = True

    # 1. Probe PostgreSQL
    try:
        res = await db.execute(text("SELECT 1"))
        if res.scalar() == 1:
            db_status = "connected"
        else:
            db_status = "unexpected_response"
            is_healthy = False
    except Exception:
        db_status = "disconnected"
        is_healthy = False

    # 2. Probe Redis
    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        pong = await client.ping()
        if pong is True:
            redis_status = "connected"
        else:
            redis_status = "unexpected_response"
            is_healthy = False
        await client.aclose()
    except Exception:
        redis_status = "disconnected"
        is_healthy = False

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "app": "EKIP",
            "version": "0.1.0",
            "database": db_status,
            "redis": redis_status,
        }

    return {
        "status": "ok",
        "app": "EKIP",
        "version": "0.1.0",
        "database": db_status,
        "redis": redis_status,
    }