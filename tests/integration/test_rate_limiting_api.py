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


@pytest.mark.asyncio
async def test_query_rate_limit_counts_only_query_requests():
    """
    Verify earlier session requests (health, register, login, collections, upload,
    documents, analytics, retrieve) are NOT counted toward RATE_LIMIT_QUERY_PER_MINUTE,
    and exactly 20 query requests succeed before the 21st returns 429.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]
        admin_email = f"query_rate_{suffix}@example.com"

        # Earlier session requests that must NOT consume query quota
        health_res = await client.get("/api/v1/health")
        assert health_res.status_code == 200
        await client.get("/api/v1/health")

        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": admin_email,
                "password": "Password123!",
                "tenant_name": f"QueryRateTenant_{suffix}",
            },
        )
        assert reg_res.status_code == 201

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": "Password123!"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        col_res = await client.post(
            "/api/v1/collections",
            headers=headers,
            json={"name": "Query Rate Limit Col"},
        )
        assert col_res.status_code == 201
        col_id = col_res.json()["id"]

        assert (await client.get("/api/v1/collections", headers=headers)).status_code == 200

        upload_res = await client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={"collection_id": col_id},
            files={"file": ("policy.txt", io.BytesIO(b"Retention period is 30 days."), "text/plain")},
        )
        assert upload_res.status_code == 202

        assert (await client.get("/api/v1/documents", headers=headers)).status_code == 200
        assert (await client.get("/api/v1/analytics/overview", headers=headers)).status_code == 200
        assert (
            await client.post(
                "/api/v1/query/retrieve",
                headers=headers,
                json={"query": "retention period", "collection_ids": [col_id]},
            )
        ).status_code == 200

        # All 20 query requests in the window must succeed (not 18)
        empty_collection_id = str(uuid.uuid4())
        for idx in range(settings.RATE_LIMIT_QUERY_PER_MINUTE):
            q_res = await client.post(
                "/api/v1/query",
                headers=headers,
                json={"query": f"Query #{idx + 1}", "collection_ids": [empty_collection_id]},
            )
            assert q_res.status_code == 200, f"Query #{idx + 1} failed unexpectedly with {q_res.status_code}: {q_res.text}"

        # 21st query request must be rate limited with 429 + Retry-After
        blocked_res = await client.post(
            "/api/v1/query",
            headers=headers,
            json={"query": "Query #21", "collection_ids": [empty_collection_id]},
        )
        assert blocked_res.status_code == 429
        assert "Retry-After" in blocked_res.headers
        assert int(blocked_res.headers["Retry-After"]) >= 1

        # Streaming query shares the same user_query quota and also returns 429
        blocked_stream = await client.post(
            "/api/v1/query/stream",
            headers=headers,
            json={"query": "Query #22", "collection_ids": [empty_collection_id]},
        )
        assert blocked_stream.status_code == 429

        # Non-query endpoints remain unaffected after hitting query rate limit
        assert (await client.get("/api/v1/health")).status_code == 200
        assert (await client.get("/api/v1/collections", headers=headers)).status_code == 200
        assert (await client.get("/api/v1/documents", headers=headers)).status_code == 200
