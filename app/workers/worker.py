from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_semantic_cache
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.job import IngestionJob
from app.rag.chunking.structural import StructuralChunker
from app.rag.cleaning import document_cleaner
from app.rag.embeddings.factory import get_embedder
from app.rag.parsing.registry import parser_registry
from app.repositories.chunks_repo import ChunksRepository
from app.repositories.documents_repo import DocumentsRepository
from app.workers.queue import BaseIngestionQueue, get_ingestion_queue

logger = logging.getLogger("ekip.ingestion_worker")


class IngestionWorker:
    def __init__(self, queue: BaseIngestionQueue | None = None) -> None:
        self.queue = queue or get_ingestion_queue()

    async def process_job(
        self,
        job_data: dict[str, Any],
        db: AsyncSession,
    ) -> int:
        job_id = uuid.UUID(job_data["job_id"])
        doc_id = uuid.UUID(job_data["document_id"])
        tenant_id = uuid.UUID(job_data["tenant_id"])
        file_path_str = job_data["file_path"]
        filename = job_data["filename"]
        mime_type = job_data["mime_type"]

        docs_repo = DocumentsRepository(db)
        chunks_repo = ChunksRepository(db)

        # 1. Fetch Job and Document records
        job_stmt = select(IngestionJob).where(
            IngestionJob.id == job_id,
            IngestionJob.tenant_id == tenant_id,
        )
        job_res = await db.execute(job_stmt)
        job = job_res.scalar_one_or_none()

        doc = await docs_repo.get_by_id(doc_id, tenant_id)
        if not doc or not job:
            raise ValueError(f"Job {job_id} or Document {doc_id} not found")

        try:
            # 2. Stage: Parsing
            job.status = "processing"
            job.stage = "parsing"
            job.progress = 20
            doc.status = "processing"
            await db.commit()

            file_path = Path(file_path_str)
            if not file_path.exists():
                raise FileNotFoundError(f"Staged upload file not found at {file_path}")
            raw_content = file_path.read_bytes()

            parser = parser_registry.get_parser(mime_type, filename)
            elements = parser.parse(raw_content, filename)

            # 3. Stage: Cleaning
            job.stage = "cleaning"
            job.progress = 40
            await db.commit()
            cleaned_elements = document_cleaner.clean(elements)

            # 4. Stage: Chunking
            job.stage = "chunking"
            job.progress = 60
            await db.commit()
            chunker = StructuralChunker(max_tokens=400, overlap_tokens=50)
            chunks_data = chunker.chunk(cleaned_elements, doc.title)

            # 5. Stage: Embedding
            job.stage = "embedding"
            job.progress = 80
            await db.commit()
            embedder = get_embedder()
            chunk_texts = [c.content for c in chunks_data]
            embeddings = await embedder.embed_documents(chunk_texts)

            # 6. Stage: Indexing / Persisting
            job.stage = "indexing"
            job.progress = 90
            await db.commit()

            db_chunks = [
                Chunk(
                    tenant_id=tenant_id,
                    collection_id=doc.collection_id,
                    document_id=doc.id,
                    doc_version=doc.current_version,
                    ordinal=c.ordinal,
                    content=c.content,
                    token_count=c.token_count,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    section_path=c.section_path,
                    metadata_={"source_file": filename},
                    embedding=emb,
                    embedding_model=embedder.model_name,
                )
                for c, emb in zip(chunks_data, embeddings)
            ]
            await chunks_repo.insert_chunks(db_chunks)

            # 7. Complete Job & Document
            now = datetime.now(timezone.utc)
            doc.status = "indexed"
            doc.error_code = None

            job.status = "completed"
            job.stage = "completed"
            job.progress = 100
            job.chunk_count = len(db_chunks)
            job.completed_at = now
            await db.commit()

            # 8. Invalidate collection cache in Redis
            cache = get_semantic_cache()
            if cache is not None:
                await cache.invalidate_collection(tenant_id, doc.collection_id)

            logger.info(
                f"Successfully processed ingestion job {job_id} for doc {doc_id}",
                extra={"chunk_count": len(db_chunks)},
            )
            return len(db_chunks)

        except Exception as e:
            await db.rollback()
            now = datetime.now(timezone.utc)
            doc.status = "failed"
            doc.error_code = str(e)[:100]

            job.status = "failed"
            job.stage = "failed"
            job.error_message = str(e)
            job.completed_at = now
            await db.commit()

            logger.error(f"Ingestion job {job_id} failed: {e}", exc_info=True)
            raise

    async def process_next_job(self, db: AsyncSession, timeout: int = 1) -> bool:
        """Pops one job from the queue and processes it. Returns True if job was processed."""
        job_data = await self.queue.dequeue(timeout=timeout)
        if not job_data:
            return False
        await self.process_job(job_data, db)
        return True
