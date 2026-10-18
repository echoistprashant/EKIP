import math
import pytest
from app.rag.embeddings.mock_embedder import MockEmbedder


@pytest.mark.asyncio
async def test_mock_embedder_dimension_and_normalization():
    embedder = MockEmbedder(dimension=1024)

    texts = [
        "What is the EU refund policy?",
        "How do I rotate database credentials in production?",
    ]

    vectors = await embedder.embed_documents(texts)

    # 1. Assert batch count and dimension
    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
    assert len(vectors[1]) == 1024

    # 2. Assert L2 Normalization (||v|| ~= 1.0)
    for vec in vectors:
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-4, f"Vector norm {norm} is not unit normalized"


@pytest.mark.asyncio
async def test_mock_embedder_determinism():
    embedder = MockEmbedder(dimension=1024)

    text = "The contractor shall comply with safety rules."
    vec1 = await embedder.embed_query(text)
    vec2 = await embedder.embed_query(text)

    # Identical text must produce identical vector
    assert vec1 == vec2

    # Different text must produce different vector
    different_vec = await embedder.embed_query("Different text")
    assert vec1 != different_vec
