from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.rag.retrieval.base import AccessScope
from app.rag.retrieval.hybrid import HybridRetriever
from app.schemas.retrieval import CandidateResponse, RetrieveRequest, RetrieveResponse

router = APIRouter(prefix="/query", tags=["Retrieval & Search"])


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_candidates(
    req: RetrieveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve ranked candidate chunks using Hybrid Search (Dense HNSW + Lexical FTS with RRF).
    Strictly pre-filtered to current user's tenant_id and optional collection_ids.
    """
    scope = AccessScope(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        collection_ids=req.collection_ids,
    )

    retriever = HybridRetriever(db)
    candidates = await retriever.retrieve(
        query=req.query,
        scope=scope,
        top_k=req.top_k,
    )

    candidate_dtos = [
        CandidateResponse(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            collection_id=c.collection_id,
            content=c.content,
            section_path=c.section_path,
            page_start=c.page_start,
            page_end=c.page_end,
            score=c.score,
            retrieval_method=c.retrieval_method,
        )
        for c in candidates
    ]

    return RetrieveResponse(
        query=req.query,
        count=len(candidate_dtos),
        candidates=candidate_dtos,
    )
