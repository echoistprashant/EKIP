from pydantic import BaseModel


class AnalyticsOverviewResponse(BaseModel):
    tenant_id: str
    total_queries: int
    total_abstentions: int
    total_cached_queries: int
    cache_hit_rate: float
    average_latency_ms: float
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    average_groundedness: float
    average_context_relevance: float
    average_answer_relevance: float
    hallucination_rate: float
    total_feedbacks: int
    positive_feedback_count: int
    positive_feedback_rate: float
    model_breakdown: dict[str, int]
    cost_by_model: dict[str, float]
