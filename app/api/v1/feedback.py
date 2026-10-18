import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.feedback import QueryFeedback
from app.models.query_log import QueryLog
from app.models.user import User
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit user feedback on a RAG query response",
)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    # 1. Verify query exists and belongs to the caller's tenant
    query_stmt = select(QueryLog).where(
        QueryLog.id == payload.query_id,
        QueryLog.tenant_id == current_user.tenant_id,
    )
    result = await db.execute(query_stmt)
    query_log = result.scalar_one_or_none()
    if not query_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query {payload.query_id} not found in current tenant scope",
        )

    # 2. Persist feedback
    feedback = QueryFeedback(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        query_id=payload.query_id,
        is_helpful=payload.is_helpful,
        rating=payload.rating,
        comment=payload.comment,
        feedback_type=payload.feedback_type,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return FeedbackResponse.model_validate(feedback)


@router.get(
    "/{query_id}",
    response_model=list[FeedbackResponse],
    summary="Retrieve feedbacks submitted for a specific query",
)
async def get_query_feedbacks(
    query_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FeedbackResponse]:
    stmt = (
        select(QueryFeedback)
        .where(
            QueryFeedback.query_id == query_id,
            QueryFeedback.tenant_id == current_user.tenant_id,
        )
        .order_by(QueryFeedback.created_at.desc())
    )
    result = await db.execute(stmt)
    feedbacks = result.scalars().all()
    return [FeedbackResponse.model_validate(fb) for fb in feedbacks]
