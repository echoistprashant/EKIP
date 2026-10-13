import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.collection import Collection
from app.models.user import User
from app.repositories.collections_repo import CollectionsRepository
from app.schemas.collection import CollectionCreate, CollectionResponse

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.get("", response_model=list[CollectionResponse])
async def list_collections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all collections belonging to current user's tenant."""
    repo = CollectionsRepository(db)
    return await repo.list_by_tenant(current_user.tenant_id)


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    req: CollectionCreate,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a collection. Admin only."""
    repo = CollectionsRepository(db)
    collection = Collection(
        tenant_id=current_user.tenant_id,
        name=req.name,
    )
    return await repo.create(collection)
