from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import re
import uuid
from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_semantic_cache
from app.core.config import settings
from app.models.document import Document
from app.models.job import IngestionJob
from app.models.user import User
from app.repositories.collections_repo import CollectionsRepository
from app.repositories.documents_repo import DocumentsRepository
from app.workers.ingestion_worker import process_document_pipeline
from app.workers.queue import get_ingestion_queue

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit
UPLOAD_CHUNK_SIZE_BYTES = 64 * 1024  # 64 KB streaming chunks
MAX_PDF_PAGES = 100


def sanitize_filename(filename: str | None) -> str:
    """
    Sanitizes an uploaded filename to prevent directory traversal and filesystem attacks.
    Uses Path(name).name plus a safe-character regex.
    """
    if not filename:
        return "uploaded_document"

    # Normalize backslashes to forward slashes before extracting basename
    normalized = filename.replace("\\", "/")
    base_name = Path(normalized).name

    # Whitelist alphanumeric, underscore, dot, hyphen
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", base_name)
    sanitized = sanitized.strip("._")
    if not sanitized:
        return "uploaded_document"
    return sanitized



class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.docs_repo = DocumentsRepository(db)
        self.cols_repo = CollectionsRepository(db)

    async def ingest_file(
        self,
        file: UploadFile,
        collection_id: uuid.UUID,
        user: User,
        async_mode: bool = False,
    ) -> tuple[Document, int, IngestionJob]:
        """
        Validates, stages and processes uploaded document.
        - If async_mode is False: processes synchronously and completes the job.
        - If async_mode is True: stages file, enqueues job to Redis, returns immediately.
        Idempotent: Re-uploading returns existing document without duplicate chunks.
        """
        # 1. Validate collection
        collection = await self.cols_repo.get_by_id(collection_id, tenant_id=user.tenant_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found or access denied",
            )

        # 2. Read in 64 KB chunks & validate size limit (streaming rejection)
        chunks: list[bytes] = []
        total_bytes = 0
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE_BYTES)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum size limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
                )
            chunks.append(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        content = b"".join(chunks)

        # 3. Calculate SHA-256 for idempotency
        content_hash = hashlib.sha256(content).hexdigest()

        # 4. Check for existing document
        existing = await self.docs_repo.get_by_hash(
            content_hash=content_hash,
            collection_id=collection_id,
            tenant_id=user.tenant_id,
        )
        if existing:
            # Fetch latest existing job if any
            job_stmt = (
                select(IngestionJob)
                .where(IngestionJob.document_id == existing.id)
                .order_by(IngestionJob.created_at.desc())
            )
            res = await self.db.execute(job_stmt)
            job = res.scalar_one_or_none()
            if not job:
                job = IngestionJob(
                    tenant_id=user.tenant_id,
                    document_id=existing.id,
                    status=existing.status,
                    stage="completed" if existing.status == "indexed" else "failed",
                    progress=100 if existing.status == "indexed" else 0,
                )
                self.db.add(job)
                await self.db.commit()
            return existing, 0, job

        filename = sanitize_filename(file.filename)

        # Validate file type and PDF magic bytes / page ceiling
        is_pdf_by_name = filename.lower().endswith(".pdf")
        is_pdf_by_mime = (file.content_type or "").lower() == "application/pdf"
        has_pdf_magic = content.startswith(b"%PDF-")

        if (is_pdf_by_name or is_pdf_by_mime) and not has_pdf_magic:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file: Missing %PDF- magic bytes signature",
            )

        if has_pdf_magic:
            mime_type = "application/pdf"
            try:
                reader = PdfReader(io.BytesIO(content))
                if len(reader.pages) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="PDF file contains no pages",
                    )
                if len(reader.pages) > MAX_PDF_PAGES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"PDF exceeds maximum allowed limit of {MAX_PDF_PAGES} pages (found {len(reader.pages)})",
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Corrupt or unreadable PDF: {e}",
                )
        elif filename.lower().endswith(".md") or (file.content_type or "").lower() == "text/markdown":
            mime_type = "text/markdown"
        elif filename.lower().endswith(".txt") or (file.content_type or "").lower() == "text/plain":
            mime_type = "text/plain"
        else:
            mime_type = file.content_type or "application/octet-stream"

        # 5. Stage raw file to persistent disk
        upload_dir = Path(settings.UPLOAD_DIR) / str(user.tenant_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{content_hash}_{filename}"
        if not file_path.resolve().is_relative_to(upload_dir.resolve()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path detected",
            )
        file_path.write_bytes(content)

        # 6. Create Document record in DB
        new_doc = Document(
            tenant_id=user.tenant_id,
            collection_id=collection_id,
            title=filename,
            mime_type=mime_type,
            content_hash=content_hash,
            storage_key=str(file_path),
            status="queued",
            current_version=1,
        )
        created_doc = await self.docs_repo.create(new_doc)

        # 7. Create IngestionJob record
        job = IngestionJob(
            tenant_id=user.tenant_id,
            document_id=created_doc.id,
            status="queued",
            stage="queued",
            progress=0,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(created_doc)
        await self.db.refresh(job)

        # 8. Dispatch according to mode
        if async_mode:
            # Enqueue to background Redis task queue
            queue = get_ingestion_queue()
            job_payload = {
                "job_id": str(job.id),
                "document_id": str(created_doc.id),
                "tenant_id": str(user.tenant_id),
                "file_path": str(file_path),
                "filename": filename,
                "mime_type": mime_type,
            }
            await queue.enqueue(job_payload)
            return created_doc, 0, job

        # Synchronous execution
        job.status = "processing"
        job.stage = "parsing"
        job.progress = 20
        await self.db.commit()

        chunk_count = await process_document_pipeline(
            document_id=created_doc.id,
            tenant_id=user.tenant_id,
            raw_content=content,
            filename=filename,
            mime_type=mime_type,
            db=self.db,
        )

        now = datetime.now(timezone.utc)
        job.status = "completed"
        job.stage = "completed"
        job.progress = 100
        job.chunk_count = chunk_count
        job.completed_at = now
        await self.db.commit()

        # Invalidate semantic cache for this collection
        cache = get_semantic_cache()
        if cache is not None:
            await cache.invalidate_collection(user.tenant_id, collection_id)

        await self.db.refresh(created_doc)
        await self.db.refresh(job)
        return created_doc, chunk_count, job
