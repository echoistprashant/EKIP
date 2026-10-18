from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.rag.retrieval.base import AccessScope, Candidate


class LexicalRetriever:
    """
    Executes lexical keyword search using PostgreSQL Full-Text Search (GIN tsvector).
    Finds exact identifiers, error codes, and acronyms that vector search may miss.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(
        self,
        query: str,
        scope: AccessScope,
        top_k: int = 50,
    ) -> list[Candidate]:
        clean_query = query.strip()
        if not clean_query:
            return []

        # Convert natural language query to tsquery safely
        tsquery_expr = func.plainto_tsquery("english", clean_query)
        rank_expr = func.ts_rank_cd(Chunk.tsv, tsquery_expr)

        stmt = select(
            Chunk,
            rank_expr.label("rank")
        ).where(
            Chunk.tenant_id == scope.tenant_id,
            Chunk.tsv.op("@@")(tsquery_expr)
        )

        if scope.collection_ids:
            stmt = stmt.where(Chunk.collection_id.in_(scope.collection_ids))

        stmt = stmt.order_by(rank_expr.desc()).limit(top_k)

        result = await self.db.execute(stmt)
        rows = result.all()

        candidates: list[Candidate] = []
        for chunk, rank in rows:
            candidates.append(
                Candidate(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    collection_id=chunk.collection_id,
                    content=chunk.content,
                    section_path=chunk.section_path or "",
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    score=float(rank),
                    retrieval_method="lexical",
                    metadata=chunk.metadata_,
                )
            )

        return candidates
