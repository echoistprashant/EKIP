from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.repositories.users_repo import UsersRepository
from app.schemas.auth import LoginRequest, TokenResponse, UserRegisterRequest


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UsersRepository(db)

    async def register(self, req: UserRegisterRequest) -> User:
        """Register a new user and create tenant if specified."""
        tenant_name = req.tenant_name or "Default Tenant"
        tenant = await self.repo.get_or_create_tenant(tenant_name)

        existing_user = await self.repo.get_by_email(req.email, tenant_id=tenant.id)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists in this tenant",
            )

        hashed_password = get_password_hash(req.password)
        new_user = User(
            tenant_id=tenant.id,
            email=req.email,
            password_hash=hashed_password,
            role=req.role,
            is_active=True,
        )
        await self.repo.create_user(new_user)
        return new_user

    async def login(self, req: LoginRequest) -> TokenResponse:
        """Authenticate user and issue JWT."""
        user = await self.repo.get_by_email(req.email)
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role,
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
