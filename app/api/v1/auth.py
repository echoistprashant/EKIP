from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    InviteCreateRequest,
    InviteResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    auth_service = AuthService(db)
    return await auth_service.register(req)


@router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    req: InviteCreateRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an invite token to invite a user with a specific role to the tenant (Admin only)."""
    auth_service = AuthService(db)
    return await auth_service.create_invite(current_user, req)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and issue access token and refresh token."""
    auth_service = AuthService(db)
    return await auth_service.login(req)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new 30-minute access token and rotated refresh token."""
    auth_service = AuthService(db)
    return await auth_service.refresh(req.refresh_token)


@router.post("/logout")
async def logout(
    req: LogoutRequest | None = None,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke refresh token(s) and logout."""
    auth_service = AuthService(db)
    token_str = req.refresh_token if req else None
    return await auth_service.logout(refresh_token=token_str, current_user=current_user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve profile of currently authenticated user."""
    return current_user
