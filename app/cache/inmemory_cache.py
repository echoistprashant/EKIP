import hashlib
import time
from typing import Any
import uuid

from app.cache.base import (
    CacheHit,
    compute_cosine_similarity,
    make_collection_fingerprint,
)
from app.schemas.query import QueryResponse


class InMemorySemanticCache:
    """
    In-memory semantic cache implementation.
    Ideal for unit tests and local development without Redis dependency.
    """

    def __init__(self, similarity_threshold: float = 0.92) -> None:
        self.similarity_threshold = similarity_threshold
        # Key: "tenant_id:fingerprint:hash" -> (response_dict, expiry)
        self._exact_store: dict[str, tuple[dict[str, Any], float]] = {}
        # Key: "tenant_id:fingerprint" -> list of (query, embedding, response_dict, expiry)
        self._semantic_store: dict[str, list[tuple[str, list[float], dict[str, Any], float]]] = {}

    def _hash_query(self, query: str) -> str:
        return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()

    async def get(
        self,
        tenant_id: uuid.UUID,
        collection_ids: list[uuid.UUID] | None,
        query: str,
        query_embedding: list[float] | None = None,
    ) -> CacheHit | None:
        fingerprint = make_collection_fingerprint(collection_ids)
        scope_prefix = f"{tenant_id}:{fingerprint}"
        q_hash = self._hash_query(query)
        exact_key = f"{scope_prefix}:{q_hash}"
        now = time.time()

        # Tier 1: Exact Hash Match (L1)
        if exact_key in self._exact_store:
            data, expiry = self._exact_store[exact_key]
            if now < expiry:
                cached_res = QueryResponse.model_validate(data)
                return CacheHit(
                    response=cached_res,
                    cache_type="exact",
                    similarity=1.0,
                    matched_query=query,
                )
            else:
                del self._exact_store[exact_key]

        # Tier 2: Semantic Vector Similarity Match (L2)
        if query_embedding is not None and scope_prefix in self._semantic_store:
            entries = self._semantic_store[scope_prefix]
            best_match = None
            best_sim = -1.0

            active_entries = []
            for q_text, emb, data, expiry in entries:
                if now < expiry:
                    active_entries.append((q_text, emb, data, expiry))
                    sim = compute_cosine_similarity(query_embedding, emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_match = (q_text, data)
            self._semantic_store[scope_prefix] = active_entries

            if best_match and best_sim >= self.similarity_threshold:
                matched_query, data = best_match
                cached_res = QueryResponse.model_validate(data)
                return CacheHit(
                    response=cached_res,
                    cache_type="semantic",
                    similarity=round(best_sim, 4),
                    matched_query=matched_query,
                )

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
        fingerprint = make_collection_fingerprint(collection_ids)
        scope_prefix = f"{tenant_id}:{fingerprint}"
        q_hash = self._hash_query(query)
        exact_key = f"{scope_prefix}:{q_hash}"
        expiry = time.time() + ttl_seconds
        data = response.model_dump()

        # Store L1
        self._exact_store[exact_key] = (data, expiry)

        # Store L2
        if query_embedding is not None:
            if scope_prefix not in self._semantic_store:
                self._semantic_store[scope_prefix] = []
            self._semantic_store[scope_prefix].append((query, query_embedding, data, expiry))

    async def invalidate_collection(
        self,
        tenant_id: uuid.UUID,
        collection_id: uuid.UUID,
    ) -> int:
        col_str = str(collection_id)
        evicted = 0

        # Exact store eviction
        keys_to_del = [
            k for k in self._exact_store if str(tenant_id) in k and (col_str in k or ":all:" in k)
        ]
        for k in keys_to_del:
            del self._exact_store[k]
            evicted += 1

        # Semantic store eviction
        sem_keys_to_del = [
            k for k in self._semantic_store if str(tenant_id) in k and (col_str in k or ":all" in k)
        ]
        for k in sem_keys_to_del:
            evicted += len(self._semantic_store[k])
            del self._semantic_store[k]

        return evicted

    async def clear(self) -> None:
        self._exact_store.clear()
        self._semantic_store.clear()
