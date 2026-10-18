import uuid
import pytest

from app.rag.citations import CitationVerifier
from app.rag.context_builder import ContextBuilder
from app.rag.prompts.manager import PromptManager
from app.rag.retrieval.base import Candidate


def make_candidate(
    content: str,
    section: str = "Overview",
    score: float = 0.9,
    chunk_id: uuid.UUID | None = None,
    doc_id: uuid.UUID | None = None,
    page_start: int | None = 1,
    page_end: int | None = 2,
) -> Candidate:
    return Candidate(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=doc_id or uuid.uuid4(),
        collection_id=uuid.uuid4(),
        content=content,
        section_path=section,
        page_start=page_start,
        page_end=page_end,
        score=score,
        retrieval_method="hybrid_rrf",
    )


class TestContextBuilder:
    def test_deduplication(self):
        builder = ContextBuilder()
        cid = uuid.uuid4()
        c1 = make_candidate("First copy of chunk", chunk_id=cid)
        c2 = make_candidate("Second copy with same id", chunk_id=cid)
        c3 = make_candidate("Unique third chunk")

        built = builder.build([c1, c2, c3], max_context_tokens=3000)
        assert len(built.sources) == 2
        assert built.sources[0].candidate.chunk_id == cid
        assert built.sources[1].candidate.chunk_id == c3.chunk_id

    def test_token_budget_enforcement(self):
        builder = ContextBuilder(chars_per_token=4.0)
        long_text = "word " * 200  # ~1000 chars -> ~250 tokens
        c1 = make_candidate(long_text)
        c2 = make_candidate(long_text)
        c3 = make_candidate(long_text)

        # Budget of 350 tokens should only accommodate 1 chunk with XML overhead
        built = builder.build([c1, c2, c3], max_context_tokens=350)
        assert len(built.sources) == 1

    def test_lost_in_the_middle_permutation(self):
        builder = ContextBuilder()
        c0 = make_candidate("Rank 1 - Best", score=0.99)
        c1 = make_candidate("Rank 2 - Second", score=0.88)
        c2 = make_candidate("Rank 3 - Third", score=0.77)
        c3 = make_candidate("Rank 4 - Fourth", score=0.66)
        c4 = make_candidate("Rank 5 - Fifth", score=0.55)

        reordered = builder.reorder_lost_in_the_middle([c0, c1, c2, c3, c4])
        # Even indices (0, 2, 4) from left: pos 0 -> c0, pos 1 -> c2, pos 2 -> c4
        # Odd indices (1, 3) from right: pos 4 -> c1, pos 3 -> c3
        # Expected order: [c0, c2, c4, c3, c1]
        assert reordered[0].content == "Rank 1 - Best"
        assert reordered[-1].content == "Rank 2 - Second"
        assert reordered[1].content == "Rank 3 - Third"
        assert reordered[-2].content == "Rank 4 - Fourth"

    def test_xml_tagging_and_attributes(self):
        builder = ContextBuilder()
        c = make_candidate(
            content="Enterprise encryption is AES-256.",
            section="Security > Encryption",
            page_start=5,
            page_end=6,
        )
        built = builder.build([c], max_context_tokens=1000)

        assert '<source id="1"' in built.context_text
        assert f'doc_id="{c.document_id}"' in built.context_text
        assert 'section="Security > Encryption"' in built.context_text
        assert 'pages="5-6"' in built.context_text
        assert "Enterprise encryption is AES-256." in built.context_text
        assert "</source>" in built.context_text
        assert 1 in built.source_map


class TestCitationVerifier:
    def test_extract_source_ids(self):
        verifier = CitationVerifier()
        text = "This is covered in [1]. Also verified in [2, 3] and [4][5]."
        ids = verifier.extract_source_ids(text)
        assert ids == [1, 2, 3, 4, 5]

    def test_valid_grounded_citation(self):
        verifier = CitationVerifier()
        c1 = make_candidate(
            "Enterprise accounts receive 24/7 dedicated telephone support.",
            section="Support SLA",
        )
        source_map = {1: c1}

        answer = "Enterprise accounts are provided with 24/7 telephone support [1]."
        result = verifier.verify(answer, source_map)

        assert len(result.citations) == 1
        assert result.citations[0].source_id == 1
        assert result.citations[0].chunk_id == c1.chunk_id
        assert result.citations[0].section_path == "Support SLA"
        assert result.grounding_score == 1.0
        assert len(result.invalid_source_ids) == 0

    def test_hallucinated_citation_source_id(self):
        verifier = CitationVerifier()
        c1 = make_candidate("Some content here.")
        source_map = {1: c1}

        # Answer cites source [9], which was not provided in context
        answer = "This completely hallucinated fact cites an imaginary source [9]."
        result = verifier.verify(answer, source_map)

        assert len(result.citations) == 0
        assert 9 in result.invalid_source_ids
        assert result.grounding_score == 0.0


class TestPromptManager:
    def test_system_prompt_loading(self):
        manager = PromptManager()
        sys_prompt = manager.get_system_prompt("v1")
        assert "Enterprise Knowledge Intelligence Assistant" in sys_prompt
        assert "CRITICAL OPERATING RULES" in sys_prompt

    def test_format_messages(self):
        manager = PromptManager()
        context = '<source id="1">\nSome text\n</source>'
        question = "What is the policy?"

        messages, ver = manager.format_messages(context, question)
        assert ver == "v1"
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert "<context>" in messages[1].content
        assert "<question>" in messages[1].content

    def test_is_abstention(self):
        manager = PromptManager()
        assert manager.is_abstention("I do not have enough information in the provided documents to answer this question.")
        assert manager.is_abstention("Based on the search, insufficient evidence was found.")
        assert not manager.is_abstention("The refund policy allows 30 days for return [1].")
