import asyncio
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_semantic_cache
from app.core.config import settings
from app.models.chunk import Chunk
from app.models.job import IngestionJob
from app.rag.chunking.structural import StructuralChunker
from app.rag.cleaning import document_cleaner
from app.rag.embeddings.factory import get_embedder
from app.rag.parsing.registry import parser_registry
from app.repositories.chunks_repo import ChunksRepository
from app.repositories.documents_repo import DocumentsRepository
from app.workers.ingestion_worker import cleanup_staged_file
from app.workers.queue import BaseIngestionQueue, get_ingestion_queue

logger = logging.getLogger("ekip.ingestion_worker")


class IngestionWorker:
    def __init__(
        self,
        queue: BaseIngestionQueue | None = None,
        max_retries: int | None = None,
        backoff_base: float | None = None,
    ) -> None:
        self.queue = queue or get_ingestion_queue()
        self.max_retries = max_retries if max_retries is not None else settings.INGESTION_MAX_RETRIES
        self.backoff_base = backoff_base if backoff_base is not None else settings.INGESTION_RETRY_BACKOFF_BASE

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
            elements = await asyncio.to_thread(parser.parse, raw_content, filename)

            # 3. Stage: Cleaning
            job.stage = "cleaning"
            job.progress = 40
            await db.commit()
            cleaned_elements = await asyncio.to_thread(document_cleaner.clean, elements)

            # 4. Stage: Chunking
            job.stage = "chunking"
            job.progress = 60
            await db.commit()
            chunker = StructuralChunker(max_tokens=400, overlap_tokens=50)
            chunks_data = await asyncio.to_thread(chunker.chunk, cleaned_elements, doc.title)

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
                for c, emb in zip(chunks_data, embeddings, strict=False)
            ]
            await chunks_repo.insert_chunks(db_chunks)

            # 7. Complete Job & Document
            now = datetime.now(UTC)
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

            # 9. Remove temporary staged upload from local disk (all data is in Postgres)
            cleanup_staged_file(file_path, logger)

            logger.info(
                f"Successfully processed ingestion job {job_id} for doc {doc_id}",
                extra={"chunk_count": len(db_chunks)},
            )
            return len(db_chunks)

        except Exception as e:
            await db.rollback()
            now = datetime.now(UTC)
            retry_count = job_data.get("retry_count", 0)

            if retry_count < self.max_retries:
                next_attempt = retry_count + 1
                job_data["retry_count"] = next_attempt
                delay = self.backoff_base * (2 ** retry_count)

                logger.warning(
                    f"Ingestion job {job_id} failed on attempt {next_attempt}/{self.max_retries}. "
                    f"Backing off for {delay:.2f}s before retry: {e}"
                )

                job.status = "retrying"
                job.stage = "retry_backoff"
                job.error_message = f"Attempt {next_attempt}/{self.max_retries} failed: {e}"
                doc.status = "retrying"
                doc.error_code = f"RETRY_{next_attempt}"
                await db.commit()

                if delay > 0:
                    await asyncio.sleep(delay)
                await self.queue.enqueue(job_data)
                raise
            else:
                logger.error(
                    f"Ingestion job {job_id} exceeded max retries ({self.max_retries}). "
                    f"Routing to Dead-Letter Queue (DLQ). Error: {e}"
                )
                await self.queue.enqueue_dlq(job_data, error=str(e))

                doc.status = "failed"
                doc.error_code = "MAX_RETRIES_EXCEEDED"

                job.status = "failed"
                job.stage = "dead_letter_queue"
                job.error_message = f"Exceeded maximum retries ({self.max_retries}). Sent to DLQ. Error: {e}"
                job.completed_at = now
                await db.commit()
                cleanup_staged_file(Path(file_path_str), logger)
                raise

    async def process_next_job(self, db: AsyncSession, timeout: int = 1) -> bool:
        """Pops one job from the queue and processes it. Returns True if job was processed."""
        job_data = await self.queue.dequeue(timeout=timeout)
        if not job_data:
            return False
        try:
            await self.process_job(job_data, db)
            return True
        except Exception:
            return True


async def run_ingestion_worker_loop() -> None:
    """Continuous background loop consuming from Redis Ingestion Queue."""
    import asyncio

    from app.db.session import AsyncSessionLocal
    worker = IngestionWorker()
    logger.info("Background ingestion queue worker loop active")
    while True:
        try:
            async with AsyncSessionLocal() as session:
                processed = await worker.process_next_job(session, timeout=1)
                if not processed:
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("Background ingestion queue worker loop stopping")
            break
        except Exception as e:
            logger.warning(f"Error in background ingestion loop: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starting standalone Ingestion Worker process...")
    asyncio.run(run_ingestion_worker_loop())
