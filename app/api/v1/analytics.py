from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsOverviewResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics & Observability"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get aggregated telemetry, RAG Triad quality, cost, and feedback metrics",
)
async def get_analytics_overview(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverviewResponse:
    service = AnalyticsService(db)
    return await service.get_overview(current_user.tenant_id)
