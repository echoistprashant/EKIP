from typing import Literal

from app.evaluation.evaluator import RAGTriadEvaluator
from app.evaluation.models import TriadEvaluationResult


class RAGGuardrail:
    """
    Runtime Hallucination Guardrail.
    Inspects generated answers against retrieved context prior to returning to the caller.
    """

    def __init__(
        self,
        evaluator: RAGTriadEvaluator | None = None,
        policy: Literal["flag", "block"] = "flag",
    ) -> None:
        self.evaluator = evaluator or RAGTriadEvaluator()
        self.policy = policy

    async def verify(
        self,
        query: str,
        context: str,
        answer: str,
    ) -> tuple[str, TriadEvaluationResult]:
        """
        Validates generation against safety thresholds.
        Returns: (final_answer, evaluation_result)
        """
        result = await self.evaluator.evaluate(query=query, context=context, answer=answer)

        final_answer = answer
        if result.hallucination_warning:
            if self.policy == "block":
                final_answer = (
                    "The generated response could not be verified with sufficient confidence "
                    "against the retrieved documents."
                )
            elif self.policy == "flag":
                final_answer = answer  # Kept intact, but flagged in metadata

        return final_answer, result
