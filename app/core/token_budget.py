import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.query_log import QueryLog
from app.models.tenant import Tenant


async def check_token_budget(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """
    Enforce tenant's monthly token budget before processing a query.
    Calculates total tokens used (input + output) in the current calendar month.
    Raises HTTP 429 if current consumption >= monthly_token_budget.
    """
    tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
    t_res = await db.execute(tenant_stmt)
    tenant = t_res.scalar_one_or_none()
    if not tenant or tenant.monthly_token_budget <= 0:
        return

    now = datetime.now(UTC)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    usage_stmt = (
        select(func.coalesce(func.sum(QueryLog.input_tokens + QueryLog.output_tokens), 0))
        .where(
            QueryLog.tenant_id == tenant_id,
            QueryLog.created_at >= start_of_month,
        )
    )
    u_res = await db.execute(usage_stmt)
    used_tokens = int(u_res.scalar_one() or 0)

    if used_tokens >= tenant.monthly_token_budget:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Monthly token budget of {tenant.monthly_token_budget:,} tokens exceeded "
                f"for tenant '{tenant.name}'. Current consumption: {used_tokens:,} tokens."
            ),
        )
