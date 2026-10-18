from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.rag.embeddings.factory import get_embedder
from app.rag.retrieval.base import AccessScope, Candidate


class DenseRetriever:
    """
    Executes semantic vector search using pgvector HNSW index.
    Strictly applies tenant and collection scope pre-filtering.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(
        self,
        query: str,
        scope: AccessScope,
        top_k: int = 50,
    ) -> list[Candidate]:
        embedder = get_embedder()
        query_vector = await embedder.embed_query(query)

        # pgvector cosine_distance operator (<=>)
        # Cosine distance = 1 - cosine_similarity (0 = identical, 2 = opposite)
        distance_expr = Chunk.embedding.cosine_distance(query_vector)

        stmt = select(
            Chunk,
            distance_expr.label("distance")
        ).where(
            Chunk.tenant_id == scope.tenant_id
        )

        if scope.collection_ids:
            stmt = stmt.where(Chunk.collection_id.in_(scope.collection_ids))

        stmt = stmt.order_by(distance_expr.asc()).limit(top_k)

        result = await self.db.execute(stmt)
        rows = result.all()

        candidates: list[Candidate] = []
        for chunk, distance in rows:
            # Convert cosine distance to similarity score
            similarity = max(0.0, 1.0 - float(distance))
            candidates.append(
                Candidate(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    collection_id=chunk.collection_id,
                    content=chunk.content,
                    section_path=chunk.section_path or "",
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    score=similarity,
                    retrieval_method="dense",
                    metadata=chunk.metadata_,
                )
            )

        return candidates
