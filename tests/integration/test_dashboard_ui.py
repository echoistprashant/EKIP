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

        # Verify compiled static Tailwind CSS is referenced and dev CDN script is removed
        assert "cdn.tailwindcss.com" not in res_dash.text
        assert '<link rel="stylesheet" href="/static/css/dashboard.css">' in res_dash.text

        # Verify Font Awesome CDN retains valid SRI + CORS attributes
        assert 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css' in res_dash.text
        assert 'integrity="sha512-iecdLmaskl7CVkqkXNQ/ZH/XLlvWZOJyj7Yy7tcenmpD1ypASozpmT/E0iPtmFIB46ZmdtAc9eNBvH0H/ZpiBw=="' in res_dash.text
        assert 'crossorigin="anonymous"' in res_dash.text

        # Verify compiled Tailwind 3.4 CSS file is served from /static/css/
        res_css = await client.get("/static/css/dashboard.css")
        assert res_css.status_code == 200
        assert "text/css" in res_css.headers["content-type"]
        assert ".bg-brand-600" in res_css.text
        assert ".text-brand-700" in res_css.text
        assert ".bg-slate-50" in res_css.text
