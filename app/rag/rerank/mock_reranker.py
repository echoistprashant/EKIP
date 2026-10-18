import re
from app.rag.retrieval.base import Candidate


class MockReranker:
    """
    Deterministic Mock Reranker for tests and offline operation.
    Zero download overhead, sub-millisecond execution.
    """

    def __init__(self, boost_factor: float = 0.2) -> None:
        self.boost_factor = boost_factor

    async def rerank(
        self,
        query: str,
        candidates: list[Candidate],
        top_n: int = 5,
    ) -> list[Candidate]:
        if not candidates:
            return []

        query_tokens = set(re.findall(r"\b\w{3,}\b", query.lower()))

        scored_candidates: list[Candidate] = []
        for c in candidates:
            content_tokens = set(re.findall(r"\b\w{3,}\b", c.content.lower()))
            overlap = len(query_tokens.intersection(content_tokens))

            # Combine original score with keyword match boost, bounded between 0.0 and 1.0
            new_score = min(1.0, round(float(c.score) + (overlap * self.boost_factor), 4))

            # Create a new Candidate with updated rerank score and retrieval method
            reranked_candidate = Candidate(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                collection_id=c.collection_id,
                content=c.content,
                section_path=c.section_path,
                page_start=c.page_start,
                page_end=c.page_end,
                score=new_score,
                retrieval_method="cross_encoder_reranked",
                metadata={**c.metadata, "original_score": c.score},
            )
            scored_candidates.append(reranked_candidate)

        # Sort descending by reranked score
        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        return scored_candidates[:top_n]
