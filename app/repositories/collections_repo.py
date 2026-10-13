import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection import Collection


class CollectionsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, collection_id: uuid.UUID, tenant_id: uuid.UUID) -> Collection | None:
        """Fetch collection strictly scoped to tenant_id."""
        stmt = select(Collection).where(
            Collection.id == collection_id,
            Collection.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Collection]:
        """List all collections belonging to tenant."""
        stmt = select(Collection).where(Collection.tenant_id == tenant_id).order_by(Collection.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, collection: Collection) -> Collection:
        """Create new collection within tenant."""
        self.db.add(collection)
        await self.db.flush()
        return collection

    async def delete(self, collection_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
        """Delete collection and cascade delete documents and chunks."""
        stmt = delete(Collection).where(
            Collection.id == collection_id,
            Collection.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        return result.rowcount
