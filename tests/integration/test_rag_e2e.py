import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.query_log import QueryCitation, QueryLog


@pytest.mark.asyncio
async def test_end_to_end_rag_and_citation_verification():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]

        # 1. Register & Login Tenant A Admin
        email_a = f"admin_{suffix}@enterprise-a.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_a,
                "password": "SecurePassword123!",
                "role": "admin",
                "tenant_name": f"EnterpriseA_{suffix}",
            },
        )
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email_a, "password": "SecurePassword123!"},
        )
        token_a = login_res.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Create Knowledge Collection
        col_res = await client.post(
            "/api/v1/collections",
            headers=headers_a,
            json={"name": f"Security Handbook {suffix}"},
        )
        col_id = col_res.json()["id"]

        # 3. Ingest a document
        doc_markdown = b"""# Incident Response Protocols
## Severity 1 Triage
For Severity 1 security incidents, notify the on-call incident commander within 15 minutes.
All communication must occur on the dedicated war-room Slack channel.
"""
        files = {
            "file": ("incident_protocols.md", io.BytesIO(doc_markdown), "text/markdown"),
        }
        upload_res = await client.post(
            "/api/v1/documents/upload",
            headers=headers_a,
            data={"collection_id": col_id},
            files=files,
        )
        assert upload_res.status_code == 202

        # 4. Ask RAG question supported by the ingested document
        rag_res = await client.post(
            "/api/v1/query",
            headers=headers_a,
            json={
                "query": "What is the notification time for Severity 1 security incidents?",
                "collection_ids": [col_id],
                "top_k": 5,
            },
        )
        assert rag_res.status_code == 200
        data = rag_res.json()

        assert data["abstained"] is False
        assert len(data["answer"]) > 0
        assert len(data["citations"]) >= 1

        first_citation = data["citations"][0]
        assert first_citation["source_id"] == 1
        assert "Severity 1" in first_citation["snippet"]
        assert first_citation["relevance_score"] > 0
        assert data["query_id"] is not None
        assert data["input_tokens"] > 0
        assert data["output_tokens"] > 0

        # Verify DB persistence of query_logs and query_citations
        query_uuid = uuid.UUID(data["query_id"])
        async with AsyncSessionLocal() as session:
            stmt = select(QueryLog).where(QueryLog.id == query_uuid)
            result = await session.execute(stmt)
            log_in_db = result.scalar_one_or_none()
            assert log_in_db is not None
            assert log_in_db.abstained is False
            assert "Severity 1" in log_in_db.question

            # Verify citations in DB
            cit_stmt = select(QueryCitation).where(QueryCitation.query_id == query_uuid)
            cit_result = await session.execute(cit_stmt)
            citations_in_db = cit_result.scalars().all()
            assert len(citations_in_db) == len(data["citations"])
            assert citations_in_db[0].rank == 1

        # 5. Abstention Test: Ask question with zero matching context
        abstain_res = await client.post(
            "/api/v1/query",
            headers=headers_a,
            json={
                "query": "What is the recipe for chocolate lava cake?",
                "collection_ids": [str(uuid.uuid4())],  # non-existent collection
                "top_k": 5,
            },
        )
        assert abstain_res.status_code == 200
        abstain_data = abstain_res.json()
        assert abstain_data["abstained"] is True
        assert len(abstain_data["citations"]) == 0
        assert "not have enough information" in abstain_data["answer"]

        # Verify abstention logged in DB
        abstain_uuid = uuid.UUID(abstain_data["query_id"])
        async with AsyncSessionLocal() as session:
            stmt = select(QueryLog).where(QueryLog.id == abstain_uuid)
            result = await session.execute(stmt)
            abstain_log = result.scalar_one_or_none()
            assert abstain_log is not None
            assert abstain_log.abstained is True

        # 6. Multi-Tenant Isolation Test: Tenant B asking about Tenant A's document
        email_b = f"admin_{suffix}@enterprise-b.com"
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": email_b,
                "password": "SecurePassword123!",
                "role": "admin",
                "tenant_name": f"EnterpriseB_{suffix}",
            },
        )
        login_b = await client.post(
            "/api/v1/auth/login",
            json={"email": email_b, "password": "SecurePassword123!"},
        )
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        tenant_b_res = await client.post(
            "/api/v1/query",
            headers=headers_b,
            json={
                "query": "What is the notification time for Severity 1 security incidents?",
                "top_k": 5,
            },
        )
        assert tenant_b_res.status_code == 200
        assert tenant_b_res.json()["abstained"] is True
        assert len(tenant_b_res.json()["citations"]) == 0
