import hashlib
import uuid
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.user import User
from app.repositories.collections_repo import CollectionsRepository
from app.repositories.documents_repo import DocumentsRepository
from app.workers.ingestion_worker import process_document_pipeline

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit


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
    ) -> tuple[Document, int]:
        """
        Validates, saves and processes uploaded document.
        Idempotent: Re-uploading returns existing document without duplicate chunks.
        """
        # 1. Validate collection
        collection = await self.cols_repo.get_by_id(collection_id, tenant_id=user.tenant_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found or access denied",
            )

        # 2. Read bytes & validate size
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size limit of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB",
            )

        # 3. Calculate SHA-256 for idempotency
        content_hash = hashlib.sha256(content).hexdigest()

        # 4. Check for existing document
        existing = await self.docs_repo.get_by_hash(
            content_hash=content_hash,
            collection_id=collection_id,
            tenant_id=user.tenant_id,
        )
        if existing:
            # Idempotent response: return existing document without re-processing
            return existing, 0

        filename = file.filename or "uploaded_document"
        mime_type = file.content_type or "application/octet-stream"

        # 5. Create Document record in DB
        new_doc = Document(
            tenant_id=user.tenant_id,
            collection_id=collection_id,
            title=filename,
            mime_type=mime_type,
            content_hash=content_hash,
            storage_key=f"uploads/{user.tenant_id}/{content_hash}",
            status="queued",
            current_version=1,
        )
        created_doc = await self.docs_repo.create(new_doc)
        await self.db.commit()

        # 6. Execute ingestion pipeline (parse -> clean -> chunk -> persist)
        chunk_count = await process_document_pipeline(
            document_id=created_doc.id,
            tenant_id=user.tenant_id,
            raw_content=content,
            filename=filename,
            mime_type=mime_type,
            db=self.db,
        )

        return created_doc, chunk_count
