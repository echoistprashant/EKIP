import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_feedback_and_analytics_pipeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]

        # 1. Register & Login Tenant A Admin
        email_a = f"admin_{suffix}@enterprise-analytics.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_a,
                "password": "SecurePassword123!",
                "role": "admin",
                "tenant_name": f"AnalyticsCorp_{suffix}",
            },
        )
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email_a, "password": "SecurePassword123!"},
        )
        token_a = login_res.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Create Collection & Upload Document
        col_res = await client.post(
            "/api/v1/collections",
            headers=headers_a,
            json={"name": f"Analytics Collection {suffix}"},
        )
        col_id = col_res.json()["id"]

        doc_content = b"""# Cloud Observability Standards
## Golden Signals
The four golden signals of monitoring are latency, traffic, errors, and saturation.
Latency measures the time it takes to service a request.
"""
        files = {
            "file": ("observability.md", io.BytesIO(doc_content), "text/markdown"),
        }
        await client.post(
            "/api/v1/documents/upload",
            headers=headers_a,
            data={"collection_id": col_id},
            files=files,
        )

        # 3. Execute first query (Generates log row)
        q1_res = await client.post(
            "/api/v1/query",
            headers=headers_a,
            json={
                "query": "What are the four golden signals of monitoring?",
                "collection_ids": [col_id],
                "top_k": 5,
            },
        )
        assert q1_res.status_code == 200
        q1_data = q1_res.json()
        query_id_1 = q1_data["query_id"]

        # 4. Submit Positive Feedback on Query 1
        fb1_res = await client.post(
            "/api/v1/feedback",
            headers=headers_a,
            json={
                "query_id": query_id_1,
                "is_helpful": True,
                "rating": 5,
                "comment": "Accurate response with valid citation",
                "feedback_type": "general",
            },
        )
        assert fb1_res.status_code == 201
        fb1_data = fb1_res.json()
        assert fb1_data["is_helpful"] is True
        assert fb1_data["rating"] == 5

        # 5. Execute repeated query (Hits cache)
        q2_res = await client.post(
            "/api/v1/query",
            headers=headers_a,
            json={
                "query": "What are the four golden signals of monitoring?",
                "collection_ids": [col_id],
                "top_k": 5,
            },
        )
        assert q2_res.status_code == 200
        q2_data = q2_res.json()
        assert q2_data["cached"] is True
        query_id_2 = q2_data["query_id"]

        # 6. Submit Negative Feedback on Query 2 (to test feedback ratio)
        fb2_res = await client.post(
            "/api/v1/feedback",
            headers=headers_a,
            json={
                "query_id": query_id_2,
                "is_helpful": False,
                "rating": 2,
                "comment": "Cached response arrived fast but wanted more details",
                "feedback_type": "missing_info",
            },
        )
        assert fb2_res.status_code == 201

        # 7. Retrieve Feedback by query ID
        get_fb_res = await client.get(
            f"/api/v1/feedback/{query_id_1}",
            headers=headers_a,
        )
        assert get_fb_res.status_code == 200
        fb_list = get_fb_res.json()
        assert len(fb_list) == 1
        assert fb_list[0]["query_id"] == query_id_1

        # 8. Test cross-tenant isolation on feedback submission
        suffix_b = uuid.uuid4().hex[:8]
        email_b = f"admin_{suffix_b}@tenant-b.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_b,
                "password": "SecurePassword123!",
                "role": "admin",
                "tenant_name": f"TenantB_{suffix_b}",
            },
        )
        login_b = await client.post(
            "/api/v1/auth/login",
            json={"email": email_b, "password": "SecurePassword123!"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        # Tenant B cannot submit feedback for Tenant A's query
        cross_fb_res = await client.post(
            "/api/v1/feedback",
            headers=headers_b,
            json={
                "query_id": query_id_1,
                "is_helpful": False,
            },
        )
        assert cross_fb_res.status_code == 404

        # 9. Get Analytics Overview for Tenant A
        analytics_res = await client.get(
            "/api/v1/analytics/overview",
            headers=headers_a,
        )
        assert analytics_res.status_code == 200
        overview = analytics_res.json()

        assert overview["total_queries"] >= 2
        assert overview["total_cached_queries"] >= 1
        assert overview["cache_hit_rate"] > 0.0
        assert overview["total_feedbacks"] == 2
        assert overview["positive_feedback_count"] == 1
        assert overview["positive_feedback_rate"] == 0.50
        assert overview["average_groundedness"] > 0.0
        assert len(overview["model_breakdown"]) > 0
