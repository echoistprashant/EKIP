import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.refresh_token import get_refresh_token_manager
from app.core.security import (
    create_access_token,
    create_invite_token,
    decode_invite_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.repositories.users_repo import UsersRepository
from app.schemas.auth import (
    InviteCreateRequest,
    InviteResponse,
    LoginRequest,
    TokenResponse,
    UserRegisterRequest,
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UsersRepository(db)

    async def register(self, req: UserRegisterRequest) -> User:
        """
        Register a new user.
        - If invite_token is provided: validates the token, joins the existing tenant
          with the pre-assigned role signed by the tenant admin.
        - If no invite_token: creates a brand NEW tenant and assigns the user as 'admin'.
          Never joins an existing tenant by name, and never accepts 'role' from the client.
        """
        if req.invite_token:
            try:
                payload = decode_invite_token(req.invite_token)
                tenant_id = uuid.UUID(payload["tenant_id"])
                role = payload["role"]
            except (jwt.PyJWTError, KeyError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired invite token",
                )

            tenant = await self.repo.get_tenant_by_id(tenant_id)
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tenant specified in invite token does not exist",
                )
        else:
            tenant_name = req.tenant_name.strip() if req.tenant_name else f"Tenant-{uuid.uuid4().hex[:8]}"
            existing_tenant = await self.repo.get_tenant_by_name(tenant_name)
            if existing_tenant:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Tenant '{tenant_name}' already exists. To join an existing tenant, an invite token is required.",
                )

            tenant = await self.repo.create_tenant(tenant_name)
            role = "admin"

        existing_user = await self.repo.get_by_email(req.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        hashed_password = get_password_hash(req.password)
        new_user = User(
            tenant_id=tenant.id,
            email=req.email,
            password_hash=hashed_password,
            role=role,
            is_active=True,
        )
        await self.repo.create_user(new_user)
        return new_user

    async def create_invite(self, admin_user: User, req: InviteCreateRequest) -> InviteResponse:
        """Generate a signed, expiring invite token to join the admin's tenant."""
        expires_delta = timedelta(hours=req.expires_hours)
        token = create_invite_token(
            tenant_id=admin_user.tenant_id,
            role=req.role,
            expires_delta=expires_delta,
        )
        expires_at = datetime.now(UTC) + expires_delta
        return InviteResponse(
            invite_token=token,
            tenant_id=admin_user.tenant_id,
            role=req.role,
            expires_at=expires_at,
        )

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

        token_mgr = get_refresh_token_manager()
        refresh_token = await token_mgr.create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
        )

        return TokenResponse(
            access_token=token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Validate refresh token and issue new 30-minute access token and rotated refresh token."""
        token_mgr = get_refresh_token_manager()
        data = await token_mgr.get_and_validate_token(refresh_token)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked refresh token",
            )

        user_id = uuid.UUID(data["user_id"])
        user = await self.repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Rotate refresh token: revoke old token and issue fresh one
        await token_mgr.revoke_refresh_token(refresh_token)
        new_refresh_token = await token_mgr.create_refresh_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
        )
        new_access_token = create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role,
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str | None = None, current_user: User | None = None) -> dict[str, str]:
        """Revoke refresh token and/or all user tokens."""
        token_mgr = get_refresh_token_manager()
        if refresh_token:
            await token_mgr.revoke_refresh_token(refresh_token)
        if current_user:
            await token_mgr.revoke_all_user_tokens(current_user.id)

        return {"status": "logged_out", "detail": "Tokens successfully revoked"}
