import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_hybrid_retrieval_and_acl_scoping():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]

        # 1. Register & Login User A (Admin)
        email_a = f"admin_{suffix}@corp-a.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_a,
                "password": "password123",
                "role": "admin",
                "tenant_name": f"CorpA_{suffix}",
            },
        )
        login_a = await client.post(
            "/api/v1/auth/login",
            json={"email": email_a, "password": "password123"},
        )
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Create Collection
        col_res = await client.post(
            "/api/v1/collections",
            headers=headers_a,
            json={"name": f"Engineering Knowledge {suffix}"},
        )
        col_id = col_res.json()["id"]

        # 3. Upload Document
        doc_content = b"""# Production Database Guidelines
## Credential Rotation
To rotate database credentials safely, run the credentials vault rotation script.
Always update environment variable DB_SECRET_KEY immediately.
"""
        files = {
            "file": ("db_guidelines.md", io.BytesIO(doc_content), "text/markdown"),
        }
        upload_res = await client.post(
            "/api/v1/documents/upload",
            headers=headers_a,
            data={"collection_id": col_id},
            files=files,
        )
        assert upload_res.status_code == 202

        # 4. TEST: Query for "credentials rotation"
        query_res = await client.post(
            "/api/v1/query/retrieve",
            headers=headers_a,
            json={
                "query": "rotate database credentials",
                "collection_ids": [col_id],
                "top_k": 5,
            },
        )
        assert query_res.status_code == 200
        data = query_res.json()
        assert data["count"] >= 1
        top_cand = data["candidates"][0]
        assert "Credential Rotation" in top_cand["content"]
        assert top_cand["retrieval_method"] == "hybrid_rrf"
        assert top_cand["score"] > 0

        # 5. TEST: Pre-filtering with different non-existent collection returns empty
        empty_res = await client.post(
            "/api/v1/query/retrieve",
            headers=headers_a,
            json={
                "query": "rotate database credentials",
                "collection_ids": [str(uuid.uuid4())],
                "top_k": 5,
            },
        )
        assert empty_res.status_code == 200
        assert empty_res.json()["count"] == 0

        # 6. TEST: Tenant B cannot retrieve Tenant A's documents
        email_b = f"admin_{suffix}@corp-b.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_b,
                "password": "password123",
                "role": "admin",
                "tenant_name": f"CorpB_{suffix}",
            },
        )
        login_b = await client.post(
            "/api/v1/auth/login",
            json={"email": email_b, "password": "password123"},
        )
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        tenant_b_query = await client.post(
            "/api/v1/query/retrieve",
            headers=headers_b,
            json={
                "query": "rotate database credentials",
                "top_k": 5,
            },
        )
        assert tenant_b_query.status_code == 200
        assert tenant_b_query.json()["count"] == 0
