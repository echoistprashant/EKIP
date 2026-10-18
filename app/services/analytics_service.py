import uuid
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import QueryFeedback
from app.models.query_log import QueryLog
from app.schemas.analytics import AnalyticsOverviewResponse


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_overview(self, tenant_id: uuid.UUID) -> AnalyticsOverviewResponse:
        """
        Computes tenant-scoped aggregated telemetry, quality, cost,
        and user feedback metrics.
        """
        # 1. Aggregate core query metrics
        query_stmt = (
            select(
                func.count(QueryLog.id).label("total_queries"),
                func.coalesce(
                    func.sum(case((QueryLog.abstained.is_(True), 1), else_=0)), 0
                ).label("total_abstentions"),
                func.coalesce(
                    func.sum(case((QueryLog.model.like("%-cache"), 1), else_=0)), 0
                ).label("total_cached"),
                func.coalesce(func.avg(QueryLog.latency_ms), 0.0).label("avg_latency"),
                func.coalesce(func.sum(QueryLog.cost_usd), 0.0).label("total_cost"),
                func.coalesce(func.sum(QueryLog.input_tokens), 0).label("total_input_tokens"),
                func.coalesce(func.sum(QueryLog.output_tokens), 0).label("total_output_tokens"),
                func.coalesce(func.avg(QueryLog.groundedness_score), 1.0).label("avg_groundedness"),
                func.coalesce(
                    func.avg(QueryLog.context_relevance_score), 1.0
                ).label("avg_context_relevance"),
                func.coalesce(
                    func.avg(QueryLog.answer_relevance_score), 1.0
                ).label("avg_answer_relevance"),
                func.coalesce(
                    func.sum(case((QueryLog.hallucination_flag.is_(True), 1), else_=0)), 0
                ).label("total_hallucinations"),
            )
            .where(QueryLog.tenant_id == tenant_id)
        )
        q_result = await self.db.execute(query_stmt)
        q_row = q_result.one()

        total_queries = int(q_row.total_queries or 0)
        total_abstentions = int(q_row.total_abstentions or 0)
        total_cached = int(q_row.total_cached or 0)
        avg_latency = round(float(q_row.avg_latency or 0.0), 2)
        total_cost = round(float(q_row.total_cost or 0.0), 6)
        total_input_tokens = int(q_row.total_input_tokens or 0)
        total_output_tokens = int(q_row.total_output_tokens or 0)
        avg_groundedness = round(float(q_row.avg_groundedness or 0.0), 3)
        avg_context_relevance = round(float(q_row.avg_context_relevance or 0.0), 3)
        avg_answer_relevance = round(float(q_row.avg_answer_relevance or 0.0), 3)
        total_hallucinations = int(q_row.total_hallucinations or 0)

        cache_hit_rate = (
            round(total_cached / total_queries, 4) if total_queries > 0 else 0.0
        )
        hallucination_rate = (
            round(total_hallucinations / total_queries, 4) if total_queries > 0 else 0.0
        )

        # 2. Model breakdown and cost distribution
        model_stmt = (
            select(
                QueryLog.model,
                func.count(QueryLog.id).label("model_count"),
                func.coalesce(func.sum(QueryLog.cost_usd), 0.0).label("model_cost"),
            )
            .where(QueryLog.tenant_id == tenant_id)
            .group_by(QueryLog.model)
        )
        model_res = await self.db.execute(model_stmt)
        model_rows = model_res.all()

        model_breakdown = {row.model: int(row.model_count) for row in model_rows}
        cost_by_model = {row.model: round(float(row.model_cost), 6) for row in model_rows}

        # 3. Aggregate user feedback
        feedback_stmt = (
            select(
                func.count(QueryFeedback.id).label("total_feedback"),
                func.coalesce(
                    func.sum(case((QueryFeedback.is_helpful.is_(True), 1), else_=0)), 0
                ).label("positive_count"),
            )
            .where(QueryFeedback.tenant_id == tenant_id)
        )
        fb_result = await self.db.execute(feedback_stmt)
        fb_row = fb_result.one()

        total_feedbacks = int(fb_row.total_feedback or 0)
        positive_feedback_count = int(fb_row.positive_count or 0)
        positive_rate = (
            round(positive_feedback_count / total_feedbacks, 4)
            if total_feedbacks > 0
            else 0.0
        )

        return AnalyticsOverviewResponse(
            tenant_id=str(tenant_id),
            total_queries=total_queries,
            total_abstentions=total_abstentions,
            total_cached_queries=total_cached,
            cache_hit_rate=cache_hit_rate,
            average_latency_ms=avg_latency,
            total_cost_usd=total_cost,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_tokens=total_input_tokens + total_output_tokens,
            average_groundedness=avg_groundedness,
            average_context_relevance=avg_context_relevance,
            average_answer_relevance=avg_answer_relevance,
            hallucination_rate=hallucination_rate,
            total_feedbacks=total_feedbacks,
            positive_feedback_count=positive_feedback_count,
            positive_feedback_rate=positive_rate,
            model_breakdown=model_breakdown,
            cost_by_model=cost_by_model,
        )
