from typing import Protocol
from app.rag.retrieval.base import Candidate


class BaseReranker(Protocol):
    """Protocol for Cross-Encoder Rerankers."""

    async def rerank(
        self,
        query: str,
        candidates: list[Candidate],
        top_n: int = 5,
    ) -> list[Candidate]:
        """
        Takes raw retrieved candidates, computes deep cross-attention scores,
        and returns the top_n most relevant candidates sorted descending by score.
        """
        ...
