import asyncio
import math
from typing import Sequence
from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.rag.retrieval.base import Candidate


def _safe_sigmoid(x: float) -> float:
    """Numerically stable sigmoid function mapping raw cross-encoder logits to (0, 1)."""
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


class FastEmbedReranker:
    """
    In-process ONNX CPU Cross-Encoder Reranker using fastembed.
    Executes cross-attention between (query, candidate_document) pairs
    in an asyncio worker thread to avoid blocking the FastAPI event loop.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        self.model_name = model_name
        self._model: TextCrossEncoder | None = None

    def _get_model(self) -> TextCrossEncoder:
        if self._model is None:
            self._model = TextCrossEncoder(model_name=self.model_name)
        return self._model

    def _compute_rerank_scores(self, query: str, docs: list[str]) -> list[float]:
        model = self._get_model()
        raw_scores = list(model.rerank(query=query, documents=docs))
        return [_safe_sigmoid(float(s)) for s in raw_scores]

    async def rerank(
        self,
        query: str,
        candidates: Sequence[Candidate],
        top_n: int = 5,
    ) -> list[Candidate]:
        if not candidates:
            return []

        doc_texts = [c.content for c in candidates]

        # Offload synchronous ONNX inference to worker thread
        scores = await asyncio.to_thread(self._compute_rerank_scores, query, doc_texts)

        reranked_candidates: list[Candidate] = []
        for candidate, score in zip(candidates, scores, strict=True):
            reranked_candidates.append(
                Candidate(
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    collection_id=candidate.collection_id,
                    content=candidate.content,
                    section_path=candidate.section_path,
                    page_start=candidate.page_start,
                    page_end=candidate.page_end,
                    score=round(score, 4),
                    retrieval_method="cross_encoder_reranked",
                    metadata={
                        **candidate.metadata,
                        "original_score": candidate.score,
                        "cross_encoder_model": self.model_name,
                    },
                )
            )

        reranked_candidates.sort(key=lambda x: x.score, reverse=True)
        return reranked_candidates[:top_n]
