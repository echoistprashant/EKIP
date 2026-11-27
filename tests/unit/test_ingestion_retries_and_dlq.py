import uuid
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
