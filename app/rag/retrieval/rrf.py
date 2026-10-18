import uuid
from app.rag.retrieval.base import Candidate


def reciprocal_rank_fusion(
    dense_candidates: list[Candidate],
    lexical_candidates: list[Candidate],
    k: int = 60,
) -> list[Candidate]:
    """
    Combines ranked results from Dense and Lexical search using Reciprocal Rank Fusion.
    RRF Score(d) = sum(1 / (k + rank_i))
    Constant k=60 prevents top ranks in one list from drowning out candidates from the other.
    """
    candidate_map: dict[uuid.UUID, Candidate] = {}
    rrf_scores: dict[uuid.UUID, float] = {}

    # Process Dense candidates (1-indexed rank)
    for rank, cand in enumerate(dense_candidates, start=1):
        cid = cand.chunk_id
        candidate_map[cid] = cand
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k + rank))

    # Process Lexical candidates (1-indexed rank)
    for rank, cand in enumerate(lexical_candidates, start=1):
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
                score=rrf_scores[cid],
                retrieval_method="hybrid_rrf",
                metadata=base_cand.metadata,
            )
        )

    return fused_candidates
