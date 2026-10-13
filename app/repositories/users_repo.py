import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User


class UsersRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch user by primary key."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, tenant_id: uuid.UUID | None = None) -> User | None:
        """Fetch user by email, optionally scoped to tenant."""
        stmt = select(User).where(User.email == email)
        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, user: User) -> User:
        """Add user to database within transaction."""
        self.db.add(user)
        await self.db.flush()
        return user

    async def get_tenant_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        """Fetch tenant by ID."""
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_tenant(self, name: str) -> Tenant:
        """Fetch existing tenant by name or create a new one."""
        stmt = select(Tenant).where(Tenant.name == name)
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(name=name)
            self.db.add(tenant)
            await self.db.flush()
        return tenant
