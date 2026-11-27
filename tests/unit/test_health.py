
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient
import pytest

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_deep_health_check_healthy():
    """Verify deep health check returns 200 and connected status when DB and Redis are up."""
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "EKIP"
    assert data["version"] == "0.1.0"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_deep_health_check_database_failure_returns_503():
    """Verify deep health check returns 503 when Postgres fails."""
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("DB Connection Refused")

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_deep_health_check_redis_failure_returns_503():
    """Verify deep health check returns 503 when Redis fails."""
    with patch("redis.asyncio.from_url") as mock_from_url:
        mock_client = AsyncMock()
        mock_client.ping.side_effect = Exception("Redis Connection Timeout")
        mock_from_url.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["redis"] == "disconnected"
