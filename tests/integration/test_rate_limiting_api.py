import io
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_api_rate_limiting_returns_429():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]
        admin_email = f"rate_admin_{suffix}@example.com"

        # Register & Login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": admin_email,
                "password": "Password123!",
                "tenant_name": f"RateTenant_{suffix}",
            },
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": "Password123!"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create collection
        col_res = await client.post(
            "/api/v1/collections",
            headers=headers,
            json={"name": "Rate Limit Col"},
        )
        col_id = col_res.json()["id"]

        # Temporarily drop limit to 2 for testing
        orig_upload_limit = settings.RATE_LIMIT_UPLOAD_PER_MINUTE
        settings.RATE_LIMIT_UPLOAD_PER_MINUTE = 2

        try:
            # 1st and 2nd upload allowed
            for i in range(2):
                res = await client.post(
                    "/api/v1/documents/upload",
                    headers=headers,
                    data={"collection_id": col_id},
                    files={"file": (f"doc_{i}.txt", io.BytesIO(f"doc content {i}".encode()), "text/plain")},
                )
                assert res.status_code in [201, 202]

            # 3rd upload must hit 429
            blocked_res = await client.post(
                "/api/v1/documents/upload",
                headers=headers,
                data={"collection_id": col_id},
                files={"file": ("doc_blocked.txt", io.BytesIO(b"blocked content"), "text/plain")},
            )
            assert blocked_res.status_code == 429
            assert "Retry-After" in blocked_res.headers
            assert int(blocked_res.headers["Retry-After"]) >= 1

        finally:
            settings.RATE_LIMIT_UPLOAD_PER_MINUTE = orig_upload_limit
