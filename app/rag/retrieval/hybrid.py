import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.retrieval.base import AccessScope, Candidate
from app.rag.retrieval.dense import DenseRetriever
from app.rag.retrieval.lexical import LexicalRetriever
from app.rag.retrieval.rrf import reciprocal_rank_fusion


class HybridRetriever:
    """
    Executes Dense ANN search and Lexical Full-Text Search concurrently,
    then merges rankings using Reciprocal Rank Fusion (RRF).
    Supports optional separate dense and lexical queries (crucial for HyDE).
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dense_retriever = DenseRetriever(db)
        self.lexical_retriever = LexicalRetriever(db)

    async def retrieve(
        self,
        query: str,
        scope: AccessScope,
        top_k: int = 20,
        candidate_pool_size: int = 50,
        dense_query: str | None = None,
        lexical_query: str | None = None,
    ) -> list[Candidate]:
        """
        1. Concurrently run Dense and Lexical search with candidate_pool_size.
        2. Merge both ranked lists via Reciprocal Rank Fusion.
        3. Return top_k fused candidates.
        """
        effective_dense_query = dense_query or query
        effective_lexical_query = lexical_query or query

        dense_task = self.dense_retriever.retrieve(
            query=effective_dense_query,
            scope=scope,
            top_k=candidate_pool_size,
        )
        lexical_task = self.lexical_retriever.retrieve(
            query=effective_lexical_query,
            scope=scope,
            top_k=candidate_pool_size,
        )

        dense_results, lexical_results = await asyncio.gather(dense_task, lexical_task)

        fused = reciprocal_rank_fusion(
            dense_candidates=dense_results,
            lexical_candidates=lexical_results,
            k=60,
        )

        return fused[:top_k]
