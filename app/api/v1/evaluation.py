from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.evaluation import get_evaluator
from app.evaluation.models import EvaluationRequest, EvaluationResponse
from app.models.user import User

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Guardrails"])


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_rag_triad(
    req: EvaluationRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Evaluates RAG Triad Metrics:
    - Context Relevance: Information coverage of retrieved sources
    - Groundedness (Faithfulness): Hallucination check against sources
    - Answer Relevance: Directness and completeness in answering user query
    100% Free, local CPU execution.
    """
    evaluator = get_evaluator()
    result = await evaluator.evaluate(
        query=req.query,
        context=req.context,
        answer=req.answer,
    )

    return EvaluationResponse(
        context_relevance=result.context_relevance,
        groundedness=result.groundedness,
        answer_relevance=result.answer_relevance,
        rag_triad_score=result.rag_triad_score,
        passed_guardrails=result.passed_guardrails,
        hallucination_warning=result.hallucination_warning,
        unsupported_claims=result.unsupported_claims,
        verdict=result.verdict,
    )
