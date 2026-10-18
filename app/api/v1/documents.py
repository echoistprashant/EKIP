import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.document import Document
from app.models.job import IngestionJob
from app.models.user import User
from app.repositories.collections_repo import CollectionsRepository
from app.repositories.documents_repo import DocumentsRepository
from app.schemas.document import DocumentCreate, DocumentResponse
from app.schemas.job import IngestionJobResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    response: Response,
    collection_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    async_mode: bool = Form(default=False),
    current_user: User = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and trigger document parsing, cleaning, and structural chunking.
    Supports:
    - async_mode=False: Synchronous ingestion pipeline execution.
    - async_mode=True: Decoupled background task dispatch via Redis Ingestion Queue.
    Idempotent: Re-uploading the same file returns existing document without duplicate chunks.
    """
    service = IngestionService(db)
    doc, _, job = await service.ingest_file(
        file=file,
        collection_id=collection_id,
        user=current_user,
        async_mode=async_mode,
    )
    response.headers["X-Job-ID"] = str(job.id)
    return doc


@router.get("", response_model=list[DocumentResponse], summary="List documents for current tenant")
async def list_documents(
    collection_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents belonging to current tenant, optionally filtered by collection."""
    doc_repo = DocumentsRepository(db)
    return await doc_repo.list_by_tenant(current_user.tenant_id, collection_id)


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch real-time ingestion job lifecycle, progress, and stage diagnostics."""
    stmt = select(IngestionJob).where(
        IngestionJob.id == job_id,
        IngestionJob.tenant_id == current_user.tenant_id,
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion job not found",
        )
    return job


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


@router.get("/{document_id}/jobs", response_model=list[IngestionJobResponse])
async def list_document_jobs(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List historical and active ingestion jobs for a document."""
    stmt = (
        select(IngestionJob)
        .where(
            IngestionJob.document_id == document_id,
            IngestionJob.tenant_id == current_user.tenant_id,
        )
        .order_by(IngestionJob.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()

