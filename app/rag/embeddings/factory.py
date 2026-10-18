from functools import lru_cache
from app.core.config import settings
from app.rag.embeddings.base import BaseEmbedder
from app.rag.embeddings.fastembed_embedder import FastEmbedEmbedder
from app.rag.embeddings.mock_embedder import MockEmbedder


@lru_cache
def get_embedder() -> BaseEmbedder:
    """
    Factory function returning the singleton embedder instance based on configuration.
    Defaults to FastEmbedEmbedder in production/local or MockEmbedder in tests.
    """
    if settings.EMBEDDING_PROVIDER == "fastembed":
        return FastEmbedEmbedder(model_name=settings.EMBEDDING_MODEL)
    return MockEmbedder(dimension=settings.EMBEDDING_DIM)
