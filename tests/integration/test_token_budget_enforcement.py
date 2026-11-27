import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.query_log import QueryLog
from app.models.tenant import Tenant


@pytest.mark.asyncio
async def test_monthly_token_budget_enforcement():
    """
    Test that tenants exceeding their monthly token budget receive HTTP 429 on /query and /query/stream.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]
        admin_email = f"budget_admin_{suffix}@example.com"

        # 1. Register tenant & user
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": admin_email,
                "password": "Password123!",
                "tenant_name": f"BudgetTenant_{suffix}",
            },
        )
        assert reg_res.status_code == 201
        tenant_id = uuid.UUID(reg_res.json()["tenant_id"])
        user_id = uuid.UUID(reg_res.json()["id"])

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": "Password123!"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Set monthly_token_budget to 500 tokens in database
        async with AsyncSessionLocal() as session:
            stmt = select(Tenant).where(Tenant.id == tenant_id)
            res = await session.execute(stmt)
            tenant = res.scalar_one()
            tenant.monthly_token_budget = 500

            # Insert an existing QueryLog in the current month consuming 600 tokens
            consumed_log = QueryLog(
                tenant_id=tenant_id,
                user_id=user_id,
                question="Past question",
                answer="Past answer",
                model="test-model",
                input_tokens=400,
                output_tokens=200,
                cost_usd=0.001,
                latency_ms=100,
                created_at=datetime.now(UTC),
            )
            session.add(consumed_log)
            await session.commit()

        # 3. /api/v1/query must return 429 Too Many Requests
        query_res = await client.post(
            "/api/v1/query",
            headers=headers,
            json={"query": "Why is the sky blue?"},
        )
        assert query_res.status_code == 429
        assert "Monthly token budget" in query_res.json()["detail"]
        assert "exceeded" in query_res.json()["detail"]

        # 4. /api/v1/query/stream must also return 429 Too Many Requests
        stream_res = await client.post(
            "/api/v1/query/stream",
            headers=headers,
            json={"query": "Why is the grass green?"},
        )
        assert stream_res.status_code == 429
        assert "Monthly token budget" in stream_res.json()["detail"]

        # 5. Increase budget to 1,000,000 tokens -> query proceeds past budget check
        async with AsyncSessionLocal() as session:
            stmt = select(Tenant).where(Tenant.id == tenant_id)
            res = await session.execute(stmt)
            tenant = res.scalar_one()
            tenant.monthly_token_budget = 1_000_000
            await session.commit()

        unblocked_res = await client.post(
            "/api/v1/query",
            headers=headers,
            json={"query": "What is the capital of France?"},
        )
        # Should not be 429
        assert unblocked_res.status_code != 429
