import uuid
from app.rag.retrieval.base import Candidate


def multi_list_rrf(
    candidate_lists: list[list[Candidate]],
    k: int = 60,
    retrieval_method: str = "hybrid_rrf",
) -> list[Candidate]:
    """
    Combines ranked results across arbitrary N candidate lists using Reciprocal Rank Fusion.
    RRF Score(d) = sum(1 / (k + rank_i))
    Constant k=60 prevents top ranks in one list from drowning out candidates from the other.
    """
    candidate_map: dict[uuid.UUID, Candidate] = {}
    rrf_scores: dict[uuid.UUID, float] = {}

    for cand_list in candidate_lists:
        for rank, cand in enumerate(cand_list, start=1):
            cid = cand.chunk_id
            if cid not in candidate_map:
                candidate_map[cid] = cand
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))

    # Sort all candidates by combined RRF score descending
    sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

    fused_candidates: list[Candidate] = []
    for cid in sorted_chunk_ids:
        base_cand = candidate_map[cid]
        fused_candidates.append(
            Candidate(
                chunk_id=base_cand.chunk_id,
                document_id=base_cand.document_id,
                collection_id=base_cand.collection_id,
                content=base_cand.content,
                section_path=base_cand.section_path,
                page_start=base_cand.page_start,
                page_end=base_cand.page_end,
                score=round(rrf_scores[cid], 6),
                retrieval_method=retrieval_method,
                metadata=base_cand.metadata,
            )
        )

    return fused_candidates


def reciprocal_rank_fusion(
    dense_candidates: list[Candidate],
    lexical_candidates: list[Candidate],
    k: int = 60,
) -> list[Candidate]:
    """
    Combines ranked results from Dense and Lexical search using Reciprocal Rank Fusion.
    Maintained for clean backwards compatibility.
    """
    return multi_list_rrf(
        candidate_lists=[dense_candidates, lexical_candidates],
        k=k,
        retrieval_method="hybrid_rrf",
    )
