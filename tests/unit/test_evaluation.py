import pytest

from app.evaluation.evaluator import RAGTriadEvaluator
from app.evaluation.guardrails import RAGGuardrail


@pytest.mark.asyncio
async def test_rag_triad_grounded_answer():
    evaluator = RAGTriadEvaluator()
    query = "What is the database credential rotation policy?"
    context = (
        "Enterprise Production Guidelines: All database credentials must be rotated "
        "every 90 days using the automated vault script. The DB_SECRET_KEY must be updated."
    )
    answer = (
        "Database credentials must be rotated every 90 days using the automated vault script. "
        "Engineers must update the DB_SECRET_KEY."
    )

    result = await evaluator.evaluate(query=query, context=context, answer=answer)

    assert result.context_relevance > 0.6
    assert result.groundedness >= 0.8
    assert result.answer_relevance > 0.5
    assert result.rag_triad_score > 0.6
    assert result.passed_guardrails is True
    assert result.hallucination_warning is False
    assert len(result.unsupported_claims) == 0


@pytest.mark.asyncio
async def test_rag_triad_hallucination_detection():
    evaluator = RAGTriadEvaluator(min_groundedness_threshold=0.60)
    query = "What is the return policy for hardware?"
    context = "Hardware returns must be filed within 14 days of purchase in original packaging."

    # Answer makes up imaginary statements about cash refunds and free gift cards
    answer = (
        "Customers are entitled to an immediate cash refund within 60 days. "
        "Every return also includes a complimentary 50 dollar gift card."
    )

    result = await evaluator.evaluate(query=query, context=context, answer=answer)

    assert result.groundedness < 0.50
    assert result.hallucination_warning is True
    assert result.passed_guardrails is False
    assert result.verdict == "HALLUCINATION_DETECTED"
    assert len(result.unsupported_claims) >= 1


@pytest.mark.asyncio
async def test_rag_triad_abstention_handling():
    evaluator = RAGTriadEvaluator()
    query = "How to configure quantum encryption?"
    context = "We only support classical AES-256 encryption."
    answer = "I do not have enough information in the provided documents to answer this question."

    result = await evaluator.evaluate(query=query, context=context, answer=answer)

    # When abstaining, the model correctly refused rather than hallucinating
    assert result.groundedness == 1.0
    assert result.answer_relevance == 1.0
    assert result.hallucination_warning is False
    assert result.passed_guardrails is True


@pytest.mark.asyncio
async def test_guardrail_blocking_policy():
    evaluator = RAGTriadEvaluator(min_groundedness_threshold=0.60)
    guardrail_block = RAGGuardrail(evaluator=evaluator, policy="block")

    query = "What is the security SLA?"
    context = "Severity 1 requires 15 minute notification."
    hallucinated_answer = "All issues are resolved in 5 seconds with zero downtime guarantees."

    final_ans, res = await guardrail_block.verify(query, context, hallucinated_answer)
    assert res.hallucination_warning is True
    assert "could not be verified with sufficient confidence" in final_ans
