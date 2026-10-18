import uuid
import pytest

from app.rag.compression.extractive import ExtractiveSentenceCompressor
from app.rag.rerank.fastembed_reranker import _safe_sigmoid, FastEmbedReranker
from app.rag.rerank.mock_reranker import MockReranker
from app.rag.retrieval.base import Candidate


def make_candidate(content: str, score: float = 0.5, doc_id: uuid.UUID | None = None) -> Candidate:
    return Candidate(
        chunk_id=uuid.uuid4(),
        document_id=doc_id or uuid.uuid4(),
        collection_id=uuid.uuid4(),
        content=content,
        section_path="Main",
        page_start=1,
        page_end=1,
        score=score,
        retrieval_method="hybrid_rrf",
    )


class TestMockReranker:
    @pytest.mark.asyncio
    async def test_mock_reranker_reordering_and_top_n(self):
        reranker = MockReranker(boost_factor=0.3)
        c_low = make_candidate("Unrelated chunk about office equipment.", score=0.6)
        c_high = make_candidate("PostgreSQL 16 database credentials rotation procedure.", score=0.2)
        c_med = make_candidate("Database maintenance schedule every Sunday.", score=0.3)

        query = "database credentials rotation"
        reranked = await reranker.rerank(query, [c_low, c_high, c_med], top_n=2)

        assert len(reranked) == 2
        # c_high matches "database", "credentials", "rotation" -> highest boost
        assert reranked[0].content == c_high.content
        assert reranked[0].retrieval_method == "cross_encoder_reranked"
        assert reranked[0].score >= reranked[1].score


class TestFastEmbedRerankerSigmoid:
    def test_safe_sigmoid_numerical_stability(self):
        # Extreme negative, zero, extreme positive
        assert _safe_sigmoid(0.0) == 0.5
        assert 0.0 < _safe_sigmoid(-50.0) < 0.01
        assert 0.99 < _safe_sigmoid(50.0) <= 1.0


class TestExtractiveSentenceCompressor:
    def test_compress_chunk_preserves_header_and_focal_window(self):
        compressor = ExtractiveSentenceCompressor(window_size=1, min_sentence_score=0.2)

        content = (
            "[Document: Architecture | Section: DB Security]\n\n"
            "This document was revised by the audit board in 2024. "
            "All software engineers must review company policies annually. "
            "To rotate database credentials safely, run the vault rotation script. "
            "Always update the DB_SECRET_KEY environment variable immediately. "
            "General office hours are from 9 AM to 5 PM EST. "
            "Coffee machines are refilled on Monday mornings."
        )

        query = "rotate database credentials"
        compressed = compressor.compress_chunk_content(query, content)

        # Header must be preserved
        assert "[Document: Architecture | Section: DB Security]" in compressed
        # Focal sentence must be kept
        assert "rotate database credentials safely" in compressed
        assert "Always update the DB_SECRET_KEY" in compressed
        # Irrelevant preamble & unrelated postamble stripped
        assert "Coffee machines are refilled" not in compressed
        assert "revised by the audit board" not in compressed
        assert len(compressed) < len(content)

    def test_short_chunk_not_compressed(self):
        compressor = ExtractiveSentenceCompressor()
        short_content = "This is sentence one. This is sentence two."
        compressed = compressor.compress_chunk_content("sentence one", short_content)
        assert compressed == short_content

    def test_compress_candidates_list(self):
        compressor = ExtractiveSentenceCompressor()
        c = make_candidate(
            "Introductory sentence one. Preamble sentence two. The secret encryption key is stored in AWS KMS. This protects data at rest. Unrelated trailing text five. Random footer text six."
        )
        compressed_list = compressor.compress("encryption key", [c])

        assert len(compressed_list) == 1
        assert "encryption key is stored" in compressed_list[0].content
        assert compressed_list[0].metadata["compressed"] is True
