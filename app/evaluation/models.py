from dataclasses import dataclass, field
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EvaluationRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Original user query.")
    context: str = Field(..., min_length=1, description="Retrieved context text provided to the model.")
    answer: str = Field(..., min_length=1, description="Generated model response.")


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    context_relevance: float = Field(..., ge=0.0, le=1.0, description="RAG Triad: Context Relevance score.")
    groundedness: float = Field(..., ge=0.0, le=1.0, description="RAG Triad: Groundedness / Faithfulness score.")
    answer_relevance: float = Field(..., ge=0.0, le=1.0, description="RAG Triad: Answer Relevance score.")
    rag_triad_score: float = Field(..., ge=0.0, le=1.0, description="Composite average of Triad scores.")
    passed_guardrails: bool = Field(..., description="Whether the response passed safety thresholds.")
    hallucination_warning: bool = Field(..., description="Flag indicating potential unsupported claims.")
    unsupported_claims: list[str] = Field(default_factory=list, description="Extracted claims failing verification.")
    verdict: str = Field(..., description="Human-readable quality assessment verdict.")


@dataclass
class TriadEvaluationResult:
    """Internal evaluation result container."""
    context_relevance: float
    groundedness: float
    answer_relevance: float
    rag_triad_score: float
    passed_guardrails: bool
    hallucination_warning: bool
    unsupported_claims: list[str] = field(default_factory=list)
    verdict: str = "PASS"
    details: dict[str, Any] = field(default_factory=dict)
