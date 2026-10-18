import uuid
from app.rag.retrieval.base import Candidate
from app.rag.retrieval.rrf import reciprocal_rank_fusion


def make_dummy_candidate(cid: uuid.UUID, method: str) -> Candidate:
    return Candidate(
        chunk_id=cid,
        document_id=uuid.uuid4(),
        collection_id=uuid.uuid4(),
        content=f"Content for {cid}",
        section_path="Section 1",
        page_start=1,
        page_end=1,
        score=0.9,
        retrieval_method=method,
    )


def test_rrf_boosts_candidates_present_in_both_lists():
    id_common = uuid.uuid4()
    id_dense_only = uuid.uuid4()
    id_lexical_only = uuid.uuid4()

    # Dense ranked: [id_dense_only (rank 1), id_common (rank 2)]
    dense_candidates = [
        make_dummy_candidate(id_dense_only, "dense"),
        make_dummy_candidate(id_common, "dense"),
    ]

    # Lexical ranked: [id_lexical_only (rank 1), id_common (rank 2)]
    lexical_candidates = [
        make_dummy_candidate(id_lexical_only, "lexical"),
        make_dummy_candidate(id_common, "lexical"),
    ]

    fused = reciprocal_rank_fusion(dense_candidates, lexical_candidates, k=60)

    # id_common score = 1/(60+2) + 1/(60+2) = 2/62 ~= 0.03225
    # id_dense_only score = 1/(60+1) = 1/61 ~= 0.01639
    # id_lexical_only score = 1/(60+1) = 1/61 ~= 0.01639
    # id_common MUST be the top ranked item!
    assert len(fused) == 3
    assert fused[0].chunk_id == id_common
    assert fused[0].score > fused[1].score
    assert fused[0].retrieval_method == "hybrid_rrf"
