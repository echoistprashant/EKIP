import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document


class DocumentsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> Document | None:
        """Fetch document scoped strictly to tenant_id."""
        query = select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_hash(self, content_hash: str, collection_id: uuid.UUID, tenant_id: uuid.UUID) -> Document | None:
        """Lookup by content hash to enforce upload idempotency."""
        query = select(Document).where(
            Document.content_hash == content_hash,
            Document.collection_id == collection_id,
            Document.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, document: Document) -> Document:
        """Add new document within transaction."""
        self.db.add(document)
        await self.db.flush()
        return document

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        collection_id: uuid.UUID | None = None,
    ) -> list[Document]:
        """List documents scoped to tenant with optional collection filter."""
        stmt = select(Document).where(Document.tenant_id == tenant_id)
        if collection_id:
            stmt = stmt.where(Document.collection_id == collection_id)
        stmt = stmt.order_by(Document.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, document_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
        """Cascade delete document and its chunks scoped to tenant."""
        stmt = delete(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        return result.rowcount
