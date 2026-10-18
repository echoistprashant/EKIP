import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_streaming_rag_sse_pipeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]

        # 1. Register & Login User
        email = f"stream_{suffix}@enterprise.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "StreamPassword123!",
                "role": "admin",
                "tenant_name": f"StreamCorp_{suffix}",
            },
        )
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "StreamPassword123!"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Collection & Upload Document
        col_res = await client.post(
            "/api/v1/collections",
            headers=headers,
            json={"name": f"Streaming Collection {suffix}"},
        )
        col_id = col_res.json()["id"]

        doc_content = b"""# Enterprise Streaming SLA
## Response Guarantees
Streaming responses must maintain latency under 200ms for first token arrival.
"""
        files = {
            "file": ("streaming_sla.md", io.BytesIO(doc_content), "text/markdown"),
        }
        upload_res = await client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data={"collection_id": col_id},
            files=files,
        )
        assert upload_res.status_code == 202

        # 3. Stream Question Answering via SSE
        events_received = []
        tokens_received = []

        async with client.stream(
            "POST",
            "/api/v1/query/stream",
            headers=headers,
            json={
                "query": "What is the first token arrival latency guarantee?",
                "collection_ids": [col_id],
                "top_k": 5,
            },
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            current_event = None
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                    events_received.append(current_event)
                elif line.startswith("data: ") and current_event == "token":
                    tokens_received.append(line[6:].strip())

        # Verify stream sequence
        assert "ping" in events_received
        assert "sources" in events_received
        assert "token" in events_received
        assert "done" in events_received
        assert len(tokens_received) > 0

        # 4. Stream Abstention Test for unmatched query
        abstain_events = []
        async with client.stream(
            "POST",
            "/api/v1/query/stream",
            headers=headers,
            json={
                "query": "What is the secret baking recipe for macarons?",
                "collection_ids": [str(uuid.uuid4())],
                "top_k": 5,
            },
        ) as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    abstain_events.append(line[7:].strip())

        assert "abstention" in abstain_events

        # 5. Stream Repeated Query (Hits Semantic Cache)
        cached_done_data = None
        async with client.stream(
            "POST",
            "/api/v1/query/stream",
            headers=headers,
            json={
                "query": "What is the first token arrival latency guarantee?",
                "collection_ids": [col_id],
                "top_k": 5,
            },
        ) as response:
            assert response.status_code == 200
            current_event = None
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    current_event = line[7:].strip()
                elif line.startswith("data: ") and current_event == "done":
                    import json
                    cached_done_data = json.loads(line[6:].strip())

        assert cached_done_data is not None
        assert cached_done_data.get("cached") is True

        # 6. Verify Telemetry reflects the streaming cache hit
        overview_res = await client.get("/api/v1/analytics/overview", headers=headers)
        assert overview_res.status_code == 200
        overview = overview_res.json()
        assert overview["total_cached_queries"] >= 1
        assert overview["cache_hit_rate"] > 0.0
