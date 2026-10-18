import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.workers.worker import IngestionWorker


@pytest.mark.asyncio
async def test_async_background_ingestion_e2e_pipeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]

        # 1. Register & Login Tenant Admin
        email = f"async_admin_{suffix}@enterprise-queue.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecurePassword123!",
                "role": "admin",
                "tenant_name": f"AsyncCorp_{suffix}",
            },
        )
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "SecurePassword123!"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Knowledge Collection
        col_res = await client.post(
            "/api/v1/collections",
            headers=headers,
            json={"name": f"Async Ingestion Collection {suffix}"},
        )
        col_id = col_res.json()["id"]

        # 3. Upload Document in Asynchronous Mode (async_mode=True)
        doc_content = b"""# Disaster Recovery Architecture
## Multi-Region Failover
The secondary cold standby database in region us-west-2 takes over within 30 seconds.
All asynchronous replication streams sync every 5 seconds.
"""
        files = {
            "file": ("disaster_recovery.md", io.BytesIO(doc_content), "text/markdown"),
        }
        data = {
            "collection_id": col_id,
            "async_mode": "true",
        }

        upload_res = await client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data=data,
            files=files,
        )
        assert upload_res.status_code == 202
        doc_data = upload_res.json()
        doc_id = doc_data["id"]

        # The document is immediately returned with status "queued"
        assert doc_data["status"] == "queued"
        job_id = upload_res.headers.get("X-Job-ID")
        assert job_id is not None

        # 4. Poll Job Status (Initially "queued", progress 0)
        job_res = await client.get(
            f"/api/v1/documents/jobs/{job_id}",
            headers=headers,
        )
        assert job_res.status_code == 200
        job_info = job_res.json()
        assert job_info["status"] == "queued"
        assert job_info["progress"] == 0
        assert job_info["document_id"] == doc_id

        # 5. Background Worker picks up and processes the job from the Redis queue
        worker = IngestionWorker()
        async with AsyncSessionLocal() as session:
            processed = await worker.process_next_job(session)
            assert processed is True

        # 6. Re-poll Job Status (Now "completed", stage "completed", progress 100)
        completed_job_res = await client.get(
            f"/api/v1/documents/jobs/{job_id}",
            headers=headers,
        )
        assert completed_job_res.status_code == 200
        completed_job = completed_job_res.json()
        assert completed_job["status"] == "completed"
        assert completed_job["stage"] == "completed"
        assert completed_job["progress"] == 100
        assert completed_job["chunk_count"] >= 1
        assert completed_job["completed_at"] is not None

        # 7. Check Document Status (Now "indexed")
        doc_check_res = await client.get(
            f"/api/v1/documents/{doc_id}",
            headers=headers,
        )
        assert doc_check_res.status_code == 200
        assert doc_check_res.json()["status"] == "indexed"

        # 8. List Document Jobs endpoint
        list_jobs_res = await client.get(
            f"/api/v1/documents/{doc_id}/jobs",
            headers=headers,
        )
        assert list_jobs_res.status_code == 200
        jobs_list = list_jobs_res.json()
        assert len(jobs_list) >= 1
        assert jobs_list[0]["id"] == job_id

        # 9. Ask RAG Query against the asynchronously indexed document
        rag_res = await client.post(
            "/api/v1/query",
            headers=headers,
            json={
                "query": "What is the failover time for the secondary cold standby database?",
                "collection_ids": [col_id],
                "top_k": 5,
            },
        )
        assert rag_res.status_code == 200
        rag_data = rag_res.json()
        assert rag_data["abstained"] is False
        assert len(rag_data["citations"]) >= 1
        assert "cold standby" in rag_data["citations"][0]["snippet"]
        assert "30 sec" in rag_data["citations"][0]["snippet"]
