from functools import lru_cache

from app.evaluation.evaluator import RAGTriadEvaluator
from app.evaluation.guardrails import RAGGuardrail
from app.evaluation.models import (
    EvaluationRequest,
    EvaluationResponse,
    TriadEvaluationResult,
)


@lru_cache
def get_evaluator() -> RAGTriadEvaluator:
    return RAGTriadEvaluator()


@lru_cache
def get_guardrail() -> RAGGuardrail:
    return RAGGuardrail(evaluator=get_evaluator())


__all__ = [
    "EvaluationRequest",
    "EvaluationResponse",
    "TriadEvaluationResult",
    "RAGTriadEvaluator",
    "RAGGuardrail",
    "get_evaluator",
    "get_guardrail",
]
