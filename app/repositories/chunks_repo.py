import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chunk import Chunk


class ChunksRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, chunk_id: uuid.UUID, tenant_id: uuid.UUID) -> Chunk | None:
        """
        Fetch a chunk by ID with mandatory tenant_id scope.
        Prevents cross-tenant data leakage.
        """
        query = select(Chunk).where(
            Chunk.id == chunk_id,
            Chunk.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def insert_chunks(self, chunks: list[Chunk]) -> None:
        """Atomic batch insert of chunks in current transaction."""
        self.db.add_all(chunks)
        await self.db.flush()

    async def delete_by_document(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
        """Delete all chunks for a given document with tenant isolation."""
        stmt = delete(Chunk).where(
            Chunk.document_id == document_id,
            Chunk.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        return result.rowcount
