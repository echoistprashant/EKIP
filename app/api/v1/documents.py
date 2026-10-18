import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.repositories.collections_repo import CollectionsRepository
from app.repositories.documents_repo import DocumentsRepository
from app.schemas.document import DocumentCreate, DocumentResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    collection_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and trigger document parsing, cleaning, and structural chunking.
    Idempotent: Re-uploading the same file returns existing document without duplicate chunks.
    """
    service = IngestionService(db)
    doc, _ = await service.ingest_file(file, collection_id, current_user)

    # Invalidate semantic cache for this collection to prevent stale responses
    from app.cache import get_semantic_cache
    cache = get_semantic_cache()
    if cache is not None:
        await cache.invalidate_collection(current_user.tenant_id, collection_id)

    return doc


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def register_document(
    req: DocumentCreate,
    current_user: User = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
):
    """
    Register document metadata only.
    Editor or Admin role required.
    """
    col_repo = CollectionsRepository(db)
    collection = await col_repo.get_by_id(req.collection_id, tenant_id=current_user.tenant_id)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found or access denied",
        )

    doc_repo = DocumentsRepository(db)
    existing_doc = await doc_repo.get_by_hash(
        content_hash=req.content_hash,
        collection_id=req.collection_id,
        tenant_id=current_user.tenant_id,
    )
    if existing_doc:
        return existing_doc

    new_doc = Document(
        tenant_id=current_user.tenant_id,
        collection_id=req.collection_id,
        title=req.title,
        mime_type=req.mime_type,
        content_hash=req.content_hash,
        storage_key=req.storage_key,
        source_uri=req.source_uri,
        status="queued",
    )
    return await doc_repo.create(new_doc)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch document metadata scoped strictly to tenant."""
    doc_repo = DocumentsRepository(db)
    doc = await doc_repo.get_by_id(document_id, tenant_id=current_user.tenant_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return doc
