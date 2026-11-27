import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.user import User
from app.rag.citations import CitationVerifier
from app.rag.context_builder import ContextBuilder
from app.rag.prompts.manager import PromptManager
from app.rag.retrieval.base import Candidate
from app.schemas.query import QueryRequest
from app.services.query_service import QueryService
from app.llm.client import LLMResult, TokenUsage
from app.evaluation.models import TriadEvaluationResult


@pytest.fixture
def mock_user():
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="analyst@corp.com",
        role="member",
    )


def make_candidate(content: str, score: float = 0.95) -> Candidate:
    return Candidate(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        collection_id=uuid.uuid4(),
        content=content,
        section_path="Section 1",
        page_start=1,
        page_end=1,
        score=score,
        retrieval_method="dense",
    )


@pytest.mark.asyncio
async def test_abstention_gate_on_citation_verification_failure(mock_user, caplog):
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res
    retriever = AsyncMock()
    cand = make_candidate("Enterprise plan SLA guarantees 99.9% uptime.")
    retriever.retrieve.return_value = [cand]

    # LLM hallucinates source [99] which is not in the context
    mock_llm = AsyncMock()
    hallucinated_answer = "The SLA provides 100% uptime with instant recovery [99]."
    mock_llm.generate.return_value = LLMResult(
        content=hallucinated_answer,
        usage=TokenUsage(prompt_tokens=50, completion_tokens=20, total_tokens=70),
        model="mock-model",
        latency_ms=100,
        cost_usd=0.001,
        finish_reason="stop",
    )

    evaluator = AsyncMock()
    evaluator.evaluate.return_value = TriadEvaluationResult(
        context_relevance=1.0,
        groundedness=1.0,
        answer_relevance=1.0,
        rag_triad_score=1.0,
        passed_guardrails=True,
        hallucination_warning=False,
        unsupported_claims=[],
        verdict="PASS",
    )

    service = QueryService(
        db=db,
        retriever=retriever,
        llm_client=mock_llm,
        evaluator=evaluator,
        context_builder=ContextBuilder(),
        prompt_manager=PromptManager(),
        citation_verifier=CitationVerifier(),
    )

    req = QueryRequest(query="What is the SLA?")
    with caplog.at_level("WARNING"):
        response = await service.execute_query(req, mock_user)

    # Must return abstention answer instead of ungrounded text
    assert response.abstained is True
    assert "not have enough information" in response.answer
    assert len(response.citations) == 0
    assert response.hallucination_warning is True

    # Must log original answer for debugging
    assert any(hallucinated_answer in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_abstention_gate_on_hallucination_warning(mock_user, caplog):
    db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_res
    retriever = AsyncMock()
    cand = make_candidate("Enterprise plan SLA guarantees 99.9% uptime.")
    retriever.retrieve.return_value = [cand]

    # LLM cites source [1], but evaluator flags hallucination
    mock_llm = AsyncMock()
    ungrounded_answer = "Enterprise plan SLA guarantees 99.9% uptime [1]."
    mock_llm.generate.return_value = LLMResult(
        content=ungrounded_answer,
        usage=TokenUsage(prompt_tokens=50, completion_tokens=20, total_tokens=70),
        model="mock-model",
        latency_ms=100,
        cost_usd=0.001,
        finish_reason="stop",
    )

    evaluator = AsyncMock()
    evaluator.evaluate.return_value = TriadEvaluationResult(
        context_relevance=0.8,
        groundedness=0.3,
        answer_relevance=0.5,
        rag_triad_score=0.4,
        passed_guardrails=False,
        hallucination_warning=True,
        unsupported_claims=["Low groundedness"],
        verdict="FAIL",
    )

    service = QueryService(
        db=db,
        retriever=retriever,
        llm_client=mock_llm,
        evaluator=evaluator,
        context_builder=ContextBuilder(),
        prompt_manager=PromptManager(),
        citation_verifier=CitationVerifier(),
    )

    req = QueryRequest(query="What is the SLA?")
    with caplog.at_level("WARNING"):
        response = await service.execute_query(req, mock_user)

    # Must return abstention answer
    assert response.abstained is True
    assert "not have enough information" in response.answer
    assert len(response.citations) == 0
    assert response.hallucination_warning is True

    # Must log original answer for debugging
    assert any(ungrounded_answer in record.message for record in caplog.records)
