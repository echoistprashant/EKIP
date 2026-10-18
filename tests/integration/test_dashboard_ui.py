import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_dashboard_routes_serve_html():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test root endpoint
        res_root = await client.get("/")
        assert res_root.status_code == 200
        assert "text/html" in res_root.headers["content-type"]
        assert "Enterprise Knowledge Intelligence Platform" in res_root.text
        assert "RAG Chat Assistant" in res_root.text
        assert "Knowledge Ingestion & Queue" in res_root.text
        assert "System Telemetry & Observability" in res_root.text

        # Test /dashboard endpoint
        res_dash = await client.get("/dashboard")
        assert res_dash.status_code == 200
        assert "text/html" in res_dash.headers["content-type"]
        assert "EKIP" in res_dash.text
