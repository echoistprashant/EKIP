import uuid
import pytest

from app.llm.providers.mock_llm import MockLLMClient
from app.rag.query_transform.expansion import MultiQueryExpander
from app.rag.query_transform.hyde import HyDETransformer
from app.rag.query_transform.mock_transformer import MockQueryTransformer
from app.rag.query_transform.rewrite import QueryRewriter
from app.rag.retrieval.base import Candidate
from app.rag.retrieval.rrf import multi_list_rrf


def make_candidate(content: str, score: float = 0.5, chunk_id: uuid.UUID | None = None) -> Candidate:
    return Candidate(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=uuid.uuid4(),
        collection_id=uuid.uuid4(),
        content=content,
        section_path="Main",
        page_start=1,
        page_end=1,
        score=score,
        retrieval_method="dense",
    )


class TestMockQueryTransformer:
    @pytest.mark.asyncio
    async def test_mock_hyde(self):
        transformer = MockQueryTransformer(strategy="hyde")
        res = await transformer.transform("database credentials")
        assert res.strategy_used == "hyde"
        assert res.hypothetical_document is not None
        assert "database credentials" in res.hypothetical_document

    @pytest.mark.asyncio
    async def test_mock_expansion(self):
        transformer = MockQueryTransformer(strategy="expansion")
        res = await transformer.transform("incident response")
        assert res.strategy_used == "expansion"
        assert len(res.expanded_queries) == 3
        assert "incident response standard operating procedure" in res.expanded_queries

    @pytest.mark.asyncio
    async def test_mock_rewrite(self):
        transformer = MockQueryTransformer(strategy="rewrite")
        res = await transformer.transform("sla?")
        assert res.strategy_used == "rewrite"
        assert "Enterprise policy" in res.transformed_query


class TestHyDETransformer:
    @pytest.mark.asyncio
    async def test_hyde_with_mock_llm(self):
        mock_llm = MockLLMClient(
            default_response="All production databases require multi-factor authentication and quarterly credential rotation."
        )
        transformer = HyDETransformer(llm_client=mock_llm)
        res = await transformer.transform("How to secure production databases?")

        assert res.strategy_used == "hyde"
        assert "multi-factor authentication" in res.transformed_query
        assert res.hypothetical_document == res.transformed_query
        assert res.original_query == "How to secure production databases?"


class TestMultiQueryExpander:
    @pytest.mark.asyncio
    async def test_expansion_bullet_cleaning(self):
        raw_llm_output = (
            "1. Database security best practices\n"
            "- PostgreSQL user authentication\n"
            "* Vault credential rotation guidelines"
        )
        mock_llm = MockLLMClient(default_response=raw_llm_output)
        expander = MultiQueryExpander(llm_client=mock_llm)

        res = await expander.transform("db security")
        assert res.strategy_used == "expansion"
        assert "db security" in res.expanded_queries
        assert "Database security best practices" in res.expanded_queries
        assert "PostgreSQL user authentication" in res.expanded_queries
        assert "Vault credential rotation guidelines" in res.expanded_queries
        assert len(res.expanded_queries) == 4


class TestQueryRewriter:
    @pytest.mark.asyncio
    async def test_rewrite_cleaning(self):
        mock_llm = MockLLMClient(default_response='"Production database credential rotation protocols"')
        rewriter = QueryRewriter(llm_client=mock_llm)

        res = await rewriter.transform("rotate db pw?")
        assert res.strategy_used == "rewrite"
        # Quotes stripped
        assert res.transformed_query == "Production database credential rotation protocols"


class TestMultiListRRF:
    def test_multi_list_fusion(self):
        cid_common = uuid.uuid4()
        c_common1 = make_candidate("Common chunk across lists", chunk_id=cid_common)
        c_common2 = make_candidate("Common chunk across lists", chunk_id=cid_common)
        c_common3 = make_candidate("Common chunk across lists", chunk_id=cid_common)

        c_only1 = make_candidate("Unique to list 1")
        c_only2 = make_candidate("Unique to list 2")

        list1 = [c_common1, c_only1]
        list2 = [c_common2, c_only2]
        list3 = [c_common3]

        fused = multi_list_rrf([list1, list2, list3], k=60)

        # The candidate appearing rank 1 in all 3 lists must be highest scored
        assert fused[0].chunk_id == cid_common
        # Score = 3 * (1 / (60 + 1)) = 3 / 61 ~= 0.049180
        assert fused[0].score > fused[1].score
        assert len(fused) == 3
