import hashlib
import json
import logging
from typing import Any
import uuid
import redis.asyncio as aioredis

from app.cache.base import (
    CacheHit,
    compute_cosine_similarity,
    make_collection_fingerprint,
)
from app.schemas.query import QueryResponse

logger = logging.getLogger(__name__)


class RedisSemanticCache:
    """
    Two-Tier Redis Semantic Cache:
    - Tier 1 (L1): O(1) exact hash key lookup (<1ms latency)
    - Tier 2 (L2): In-scope Cosine Vector Similarity lookup across cached query embeddings (<15ms latency)
    Strictly isolated by tenant_id and collection scope fingerprint.
    Includes automatic graceful degradation: if Redis is unavailable, bypasses cache cleanly.
    """

    def __init__(
        self,
        redis_url: str,
        similarity_threshold: float = 0.92,
    ) -> None:
        self.redis_url = redis_url
        self.similarity_threshold = similarity_threshold
        self._client: aioredis.Redis | None = None

    def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=2.0,
            )
        return self._client

    def _hash_query(self, query: str) -> str:
        return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()

    async def get(
        self,
        tenant_id: uuid.UUID,
        collection_ids: list[uuid.UUID] | None,
        query: str,
        query_embedding: list[float] | None = None,
    ) -> CacheHit | None:
        try:
            client = self._get_client()
            fingerprint = make_collection_fingerprint(collection_ids)
            scope = f"{tenant_id}:{fingerprint}"
            q_hash = self._hash_query(query)
            exact_key = f"ekip:cache:exact:{scope}:{q_hash}"

            # Tier 1: Exact Hash Match (L1)
            cached_json = await client.get(exact_key)
            if cached_json:
                data = json.loads(cached_json)
                cached_res = QueryResponse.model_validate(data)
                return CacheHit(
                    response=cached_res,
                    cache_type="exact",
                    similarity=1.0,
                    matched_query=query,
                )

            # Tier 2: Semantic Vector Similarity Match (L2)
            if query_embedding is not None:
                index_set_key = f"ekip:cache:sem_set:{scope}"
                doc_keys = await client.smembers(index_set_key)
                if not doc_keys:
                    return None

                best_match = None
                best_sim = -1.0
                stale_keys = []

                for doc_key in doc_keys:
                    entry_raw = await client.get(doc_key)
                    if not entry_raw:
                        stale_keys.append(doc_key)
                        continue

                    entry = json.loads(entry_raw)
                    cached_emb = entry.get("embedding", [])
                    sim = compute_cosine_similarity(query_embedding, cached_emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_match = entry

                # Clean up expired doc keys from the set in background
                if stale_keys:
                    await client.srem(index_set_key, *stale_keys)

                if best_match and best_sim >= self.similarity_threshold:
                    cached_res = QueryResponse.model_validate(best_match["response"])
                    return CacheHit(
                        response=cached_res,
                        cache_type="semantic",
                        similarity=round(best_sim, 4),
                        matched_query=best_match["query"],
                    )

            return None
        except Exception as exc:
            logger.warning("Redis cache get error, bypassing cache: %s", exc)
            return None

    async def set(
        self,
        tenant_id: uuid.UUID,
        collection_ids: list[uuid.UUID] | None,
        query: str,
        query_embedding: list[float] | None,
        response: QueryResponse,
        ttl_seconds: int = 86400,
    ) -> None:
        try:
            client = self._get_client()
            fingerprint = make_collection_fingerprint(collection_ids)
            scope = f"{tenant_id}:{fingerprint}"
            q_hash = self._hash_query(query)
            exact_key = f"ekip:cache:exact:{scope}:{q_hash}"
            response_dict = response.model_dump()

            # Store Tier 1 (L1)
            await client.set(exact_key, json.dumps(response_dict, default=str), ex=ttl_seconds)

            # Store Tier 2 (L2)
            if query_embedding is not None:
                doc_id = uuid.uuid4().hex[:12]
                doc_key = f"ekip:cache:sem_doc:{scope}:{doc_id}"
                index_set_key = f"ekip:cache:sem_set:{scope}"

                payload = {
                    "query": query,
                    "embedding": query_embedding,
                    "response": response_dict,
                }
                await client.set(doc_key, json.dumps(payload, default=str), ex=ttl_seconds)
                await client.sadd(index_set_key, doc_key)
                await client.expire(index_set_key, ttl_seconds)
        except Exception as exc:
            logger.warning("Redis cache set error: %s", exc)

    async def invalidate_collection(
        self,
        tenant_id: uuid.UUID,
        collection_id: uuid.UUID,
    ) -> int:
        try:
            client = self._get_client()
            col_str = str(collection_id)
            tid_str = str(tenant_id)
            evicted = 0

            # Find matching keys
            cursor = 0
            patterns = [
                f"ekip:cache:*{tid_str}*{col_str}*",
                f"ekip:cache:*{tid_str}*all*",
            ]
            for pattern in patterns:
                cursor = 0
                while True:
                    cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
                    if keys:
                        await client.delete(*keys)
                        evicted += len(keys)
                    if cursor == 0:
                        break

            return evicted
        except Exception as exc:
            logger.warning("Redis cache invalidation error: %s", exc)
            return 0

    async def clear(self) -> None:
        try:
            client = self._get_client()
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor=cursor, match="ekip:cache:*", count=100)
                if keys:
                    await client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning("Redis cache clear error: %s", exc)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
