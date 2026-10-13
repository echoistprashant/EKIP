import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.chunk import Chunk


@pytest.mark.asyncio
async def test_full_document_upload_and_ingestion_pipeline(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]
        editor_email = f"editor_{suffix}@tenant.com"

        # 1. Register & Login Editor
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": editor_email,
                "password": "password123",
                "role": "admin",  # Admin can create collection & upload
                "tenant_name": f"Tenant_{suffix}",
            },
        )
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": editor_email, "password": "password123"},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Collection
        col_res = await client.post(
            "/api/v1/collections",
            headers=headers,
            json={"name": f"Knowledge Base {suffix}"},
        )
        col_id = col_res.json()["id"]

        # 3. Prepare Markdown document
        doc_content = b"""# Database Runbook
## Replication Setup
To configure read replicas, update the patroni configuration file and restart.

## Failover Procedure
In the event of primary failure, patroni elects a new leader automatically.
"""
        files = {
            "file": ("database_runbook.md", io.BytesIO(doc_content), "text/markdown"),
        }
        data = {
            "collection_id": col_id,
        }

        # 4. Upload document
        upload_res = await client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data=data,
            files=files,
        )
        assert upload_res.status_code == 202
        doc_data = upload_res.json()
        assert doc_data["status"] == "indexed"
        doc_id = uuid.UUID(doc_data["id"])

        # 5. Verify Chunks in PostgreSQL
        stmt = select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.ordinal)
        result = await db_session.execute(stmt)
        chunks = list(result.scalars().all())

        assert len(chunks) >= 2
        assert "Database Runbook" in chunks[0].content
        assert chunks[0].section_path != ""
        assert chunks[0].token_count > 0

        # 6. IDEMPOTENCY TEST: Re-uploading identical file returns same document
        reupload_files = {
            "file": ("database_runbook.md", io.BytesIO(doc_content), "text/markdown"),
        }
        reupload_res = await client.post(
            "/api/v1/documents/upload",
            headers=headers,
            data=data,
            files=reupload_files,
        )
        assert reupload_res.status_code == 202
        assert reupload_res.json()["id"] == str(doc_id)

        # Ensure no duplicate chunks were created
        result_after = await db_session.execute(stmt)
        chunks_after = list(result_after.scalars().all())
        assert len(chunks_after) == len(chunks)
