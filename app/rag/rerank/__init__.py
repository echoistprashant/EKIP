from functools import lru_cache

from app.core.config import settings
from app.rag.rerank.base import BaseReranker
from app.rag.rerank.fastembed_reranker import FastEmbedReranker
from app.rag.rerank.mock_reranker import MockReranker


@lru_cache
def get_reranker() -> BaseReranker:
    """
    Factory function providing the configured Cross-Encoder Reranker.
    Defaults to MockReranker for deterministic sub-millisecond execution in tests,
    or FastEmbedReranker for in-process ONNX CPU reranking.
    """
    if settings.RERANKER_PROVIDER == "fastembed":
        return FastEmbedReranker(model_name=settings.RERANKER_MODEL)
    return MockReranker()


__all__ = [
    "BaseReranker",
    "FastEmbedReranker",
    "MockReranker",
    "get_reranker",
]
