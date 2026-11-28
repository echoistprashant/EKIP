import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.document import Document
from app.models.job import IngestionJob
from app.workers.queue import InMemoryIngestionQueue
from app.workers.worker import IngestionWorker


@pytest.mark.asyncio
async def test_inmemory_dlq_operations():
    q = InMemoryIngestionQueue()
    assert await q.dlq_size() == 0

    item = {"job_id": str(uuid.uuid4()), "filename": "broken.pdf"}
    await q.enqueue_dlq(item, error="Corrupted header")

    assert await q.dlq_size() == 1
    dlq_item = await q.dequeue_dlq(timeout=1)
    assert dlq_item is not None
    assert dlq_item["job_id"] == item["job_id"]
    assert dlq_item["dlq_error"] == "Corrupted header"
    assert "dlq_at" in dlq_item
    assert await q.dlq_size() == 0


@pytest.mark.asyncio
async def test_worker_retries_with_backoff_before_dlq():
    q = InMemoryIngestionQueue()
    worker = IngestionWorker(queue=q, max_retries=2, backoff_base=0.01)

    tenant_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_job = IngestionJob(
        id=job_id,
        tenant_id=tenant_id,
        document_id=doc_id,
        status="queued",
    )
    mock_doc = Document(
        id=doc_id,
        tenant_id=tenant_id,
        collection_id=uuid.uuid4(),
        title="Failing Doc",
        status="queued",
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_job
    mock_db.execute.return_value = mock_res

    job_data = {
        "job_id": str(job_id),
        "document_id": str(doc_id),
        "tenant_id": str(tenant_id),
        "file_path": "non_existent_file_path.pdf",
        "filename": "failing.pdf",
        "mime_type": "application/pdf",
        "retry_count": 0,
    }

    with patch("app.workers.worker.DocumentsRepository") as MockDocsRepo:
        docs_repo = AsyncMock()
        docs_repo.get_by_id.return_value = mock_doc
        MockDocsRepo.return_value = docs_repo

        # Attempt 1: retry_count=0 -> should retry and re-enqueue
        with pytest.raises(FileNotFoundError):
            await worker.process_job(job_data, mock_db)

        assert job_data["retry_count"] == 1
        assert mock_job.status == "retrying"
        assert mock_doc.status == "retrying"
        assert await q.qsize() == 1
        assert await q.dlq_size() == 0

        # Attempt 2: retry_count=1 -> should retry again and re-enqueue
        requeued_job = await q.dequeue()
        assert requeued_job is not None
        with pytest.raises(FileNotFoundError):
            await worker.process_job(requeued_job, mock_db)

        assert requeued_job["retry_count"] == 2
        assert mock_job.status == "retrying"
        assert await q.qsize() == 1
        assert await q.dlq_size() == 0

        # Attempt 3: retry_count=2 (max_retries reached) -> should route to DLQ
        final_job = await q.dequeue()
        assert final_job is not None
        with pytest.raises(FileNotFoundError):
            await worker.process_job(final_job, mock_db)

        assert mock_job.status == "failed"
        assert mock_job.stage == "dead_letter_queue"
        assert mock_doc.status == "failed"
        assert mock_doc.error_code == "MAX_RETRIES_EXCEEDED"
        assert await q.qsize() == 0
        assert await q.dlq_size() == 1

        # Check DLQ content
        dead_letter = await q.dequeue_dlq()
        assert dead_letter is not None
        assert dead_letter["job_id"] == str(job_id)
        assert "not found" in dead_letter["dlq_error"].lower()


@pytest.mark.asyncio
async def test_worker_deletes_staged_file_on_success_and_preserves_on_retry():
    """Staged upload must be deleted after successful ingestion, kept across retries, and cleaned up on DLQ."""
    q = InMemoryIngestionQueue()
    worker = IngestionWorker(queue=q, max_retries=1, backoff_base=0.0)

    tenant_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    with tempfile.TemporaryDirectory() as temp_dir:
        staged_file = Path(temp_dir) / "sample.txt"
        staged_file.write_bytes(b"Enterprise knowledge paragraph for worker cleanup test.")

        mock_db = AsyncMock()
        mock_job = IngestionJob(id=job_id, tenant_id=tenant_id, document_id=doc_id, status="queued")
        mock_doc = Document(
            id=doc_id,
            tenant_id=tenant_id,
            collection_id=uuid.uuid4(),
            title="sample.txt",
            status="queued",
            current_version=1,
        )
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_res

        job_data = {
            "job_id": str(job_id),
            "document_id": str(doc_id),
            "tenant_id": str(tenant_id),
            "file_path": str(staged_file),
            "filename": "sample.txt",
            "mime_type": "text/plain",
            "retry_count": 0,
        }

        with (
            patch("app.workers.worker.DocumentsRepository") as MockDocsRepo,
            patch("app.workers.worker.ChunksRepository") as MockChunksRepo,
            patch("app.workers.worker.get_semantic_cache", return_value=None),
        ):
            docs_repo = AsyncMock()
            docs_repo.get_by_id.return_value = mock_doc
            MockDocsRepo.return_value = docs_repo

            chunks_repo = AsyncMock()
            chunks_repo.insert_chunks.return_value = None
            MockChunksRepo.return_value = chunks_repo

            chunk_count = await worker.process_job(job_data, mock_db)
            assert chunk_count >= 1
            assert mock_doc.status == "indexed"
            assert mock_job.status == "completed"
            assert not staged_file.exists()

        # Now verify retry preserves file, then terminal DLQ failure removes it
        retry_file = Path(temp_dir) / "retry_fail.txt"
        retry_file.write_bytes(b"Retry failure content")
        retry_job_data = {
            "job_id": str(job_id),
            "document_id": str(doc_id),
            "tenant_id": str(tenant_id),
            "file_path": str(retry_file),
            "filename": "retry_fail.txt",
            "mime_type": "text/plain",
            "retry_count": 0,
        }

        with (
            patch("app.workers.worker.DocumentsRepository") as MockDocsRepo,
            patch("app.workers.worker.ChunksRepository") as MockChunksRepo,
        ):
            docs_repo = AsyncMock()
            docs_repo.get_by_id.return_value = mock_doc
            MockDocsRepo.return_value = docs_repo

            chunks_repo = AsyncMock()
            chunks_repo.insert_chunks.side_effect = RuntimeError("DB failure")
            MockChunksRepo.return_value = chunks_repo

            with pytest.raises(RuntimeError, match="DB failure"):
                await worker.process_job(retry_job_data, mock_db)
            assert retry_file.exists()  # Preserved for retry

            requeued = await q.dequeue()
            assert requeued is not None
            with pytest.raises(RuntimeError, match="DB failure"):
                await worker.process_job(requeued, mock_db)
            assert not retry_file.exists()  # Cleaned up after DLQ
