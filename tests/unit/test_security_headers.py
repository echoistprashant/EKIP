import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_security_headers_present_on_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.headers["X-Frame-Options"] == "DENY"
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "max-age=31536000" in res.headers["Strict-Transport-Security"]
        assert "includeSubDomains" in res.headers["Strict-Transport-Security"]


@pytest.mark.asyncio
async def test_security_headers_present_on_error_responses():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 401 Unauthorized
        res = await client.get("/api/v1/collections")
        assert res.status_code == 401
        assert res.headers["X-Frame-Options"] == "DENY"
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "max-age=31536000" in res.headers["Strict-Transport-Security"]

        # 404 Not Found
        res_404 = await client.get("/api/v1/nonexistent-route-xyz")
        assert res_404.status_code == 404
        assert res_404.headers["X-Frame-Options"] == "DENY"
        assert res_404.headers["X-Content-Type-Options"] == "nosniff"
        assert res_404.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "max-age=31536000" in res_404.headers["Strict-Transport-Security"]


@pytest.mark.asyncio
async def test_security_headers_present_on_dashboard_html():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/dashboard")
        assert res.status_code == 200
        assert res.headers["X-Frame-Options"] == "DENY"
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "max-age=31536000" in res.headers["Strict-Transport-Security"]
