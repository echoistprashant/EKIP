import uuid
import pytest

from app.cache.base import compute_cosine_similarity
from app.cache.inmemory_cache import InMemorySemanticCache
from app.cache.redis_cache import RedisSemanticCache
from app.schemas.query import CitationItem, QueryResponse


def make_dummy_response(query: str, answer: str = "Test answer") -> QueryResponse:
    return QueryResponse(
        query=query,
        answer=answer,
        citations=[
            CitationItem(
                source_id=1,
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                section_path="Section A",
                snippet="Test snippet",
                relevance_score=0.95,
            )
        ],
        abstained=False,
        model="mock-model",
        prompt_version="v1",
        input_tokens=100,
        output_tokens=25,
        cost_usd=0.0001,
        latency_ms=150,
        query_id=uuid.uuid4(),
    )


def test_cosine_similarity_calculation():
    # Identical vectors -> 1.0
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert compute_cosine_similarity(v1, v2) == 1.0

    # Orthogonal vectors -> 0.0
    v3 = [0.0, 1.0, 0.0]
    assert compute_cosine_similarity(v1, v3) == 0.0


@pytest.mark.asyncio
async def test_inmemory_exact_and_semantic_cache():
    cache = InMemorySemanticCache(similarity_threshold=0.90)
    tenant_id = uuid.uuid4()
    col_id = uuid.uuid4()

    q1 = "What is the policy for Severity 1 outages?"
    # Normalized 4-dimensional dummy embeddings for testing
    emb1 = [1.0, 0.0, 0.0, 0.0]
    res1 = make_dummy_response(q1, "Notify incident commander in 15 mins.")

    # 1. Set cache
    await cache.set(
        tenant_id=tenant_id,
        collection_ids=[col_id],
        query=q1,
        query_embedding=emb1,
        response=res1,
    )

    # 2. Exact match hit
    hit_exact = await cache.get(
        tenant_id=tenant_id,
        collection_ids=[col_id],
        query=q1,
    )
    assert hit_exact is not None
    assert hit_exact.cache_type == "exact"
    assert hit_exact.response.answer == res1.answer

    # 3. Semantic match hit (high cosine similarity ~0.99)
    q2 = "Severity 1 outage notification policy?"
    emb2 = [0.99, 0.1, 0.0, 0.0]
    # Normalize emb2
    mag = sum(x**2 for x in emb2) ** 0.5
    emb2_norm = [x / mag for x in emb2]

    hit_semantic = await cache.get(
        tenant_id=tenant_id,
        collection_ids=[col_id],
        query=q2,
        query_embedding=emb2_norm,
    )
    assert hit_semantic is not None
    assert hit_semantic.cache_type == "semantic"
    assert hit_semantic.similarity >= 0.90
    assert hit_semantic.matched_query == q1

    # 4. Semantic match miss (low cosine similarity < 0.90)
    q3 = "How to make espresso?"
    emb3 = [0.1, 0.99, 0.0, 0.0]
    hit_miss = await cache.get(
        tenant_id=tenant_id,
        collection_ids=[col_id],
        query=q3,
        query_embedding=emb3,
    )
    assert hit_miss is None

    # 5. Tenant Isolation check: Tenant B gets cache miss for Tenant A's query
    tenant_b = uuid.uuid4()
    hit_tenant_b = await cache.get(
        tenant_id=tenant_b,
        collection_ids=[col_id],
        query=q1,
    )
    assert hit_tenant_b is None

    # 6. Invalidation check
    evicted = await cache.invalidate_collection(tenant_id, col_id)
    assert evicted >= 1
    hit_after_invalidation = await cache.get(
        tenant_id=tenant_id,
        collection_ids=[col_id],
        query=q1,
    )
    assert hit_after_invalidation is None


@pytest.mark.asyncio
async def test_redis_semantic_cache_live():
    redis_url = "redis://localhost:6379/0"
    cache = RedisSemanticCache(redis_url=redis_url, similarity_threshold=0.90)
    await cache.clear()

    tenant_id = uuid.uuid4()
    col_id = uuid.uuid4()

    q1 = "Production database credential rotation?"
    emb1 = [1.0, 0.0, 0.0, 0.0]
    res1 = make_dummy_response(q1, "Use vault rotation script.")

    # 1. Set cache in Redis
    await cache.set(
        tenant_id=tenant_id,
        collection_ids=[col_id],
        query=q1,
        query_embedding=emb1,
        response=res1,
        ttl_seconds=300,
    )

    # 2. Test exact hit from Redis
    hit_exact = await cache.get(
        tenant_id=tenant_id,
        collection_ids=[col_id],
        query=q1,
    )
    assert hit_exact is not None
    assert hit_exact.cache_type == "exact"
    assert "vault rotation" in hit_exact.response.answer

    # 3. Test semantic hit from Redis
    q2 = "how do I rotate production db credentials?"
    emb2 = [0.98, 0.1, 0.0, 0.0]
    mag = sum(x**2 for x in emb2) ** 0.5
    emb2_norm = [x / mag for x in emb2]

    hit_semantic = await cache.get(
        tenant_id=tenant_id,
        collection_ids=[col_id],
        query=q2,
        query_embedding=emb2_norm,
    )
    assert hit_semantic is not None
    assert hit_semantic.cache_type == "semantic"
    assert hit_semantic.similarity >= 0.90

    # 4. Clean up
    await cache.clear()
    await cache.close()
