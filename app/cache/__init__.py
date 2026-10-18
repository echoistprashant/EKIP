from functools import lru_cache

from app.core.config import settings
from app.cache.base import BaseSemanticCache, CacheHit
from app.cache.inmemory_cache import InMemorySemanticCache
from app.cache.redis_cache import RedisSemanticCache


@lru_cache
def get_semantic_cache() -> BaseSemanticCache | None:
    """
    Factory returning configured semantic caching provider.
    Defaults to RedisSemanticCache using settings.REDIS_URL,
    or InMemorySemanticCache for local in-memory testing.
    """
    if not settings.ENABLE_SEMANTIC_CACHE:
        return None

    if settings.SEMANTIC_CACHE_PROVIDER == "redis":
        return RedisSemanticCache(
            redis_url=settings.REDIS_URL,
            similarity_threshold=settings.SEMANTIC_CACHE_THRESHOLD,
        )

    return InMemorySemanticCache(
        similarity_threshold=settings.SEMANTIC_CACHE_THRESHOLD,
    )


__all__ = [
    "BaseSemanticCache",
    "CacheHit",
    "RedisSemanticCache",
    "InMemorySemanticCache",
    "get_semantic_cache",
]
