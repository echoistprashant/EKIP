from functools import lru_cache

from app.core.config import settings
from app.rag.compression.extractive import ExtractiveSentenceCompressor


@lru_cache
def get_compressor() -> ExtractiveSentenceCompressor | None:
    if settings.ENABLE_CONTEXT_COMPRESSION:
        return ExtractiveSentenceCompressor(window_size=1)
    return None


__all__ = [
    "ExtractiveSentenceCompressor",
    "get_compressor",
]
