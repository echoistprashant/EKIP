import asyncio
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import ensure_upload_dir_writable, lifespan
from app.models.document import Document
from app.workers.ingestion_worker import process_document_pipeline


@pytest.mark.asyncio
async def test_lifespan_worker_toggle():
    """Verify lifespan respects RUN_IN_PROCESS_WORKER setting."""
    fake_app = MagicMock()

    # When False, no worker task is created
    with patch("app.main.settings.RUN_IN_PROCESS_WORKER", False), \
         patch("app.main.run_ingestion_worker_loop") as mock_loop:
        async with lifespan(fake_app):
            pass
        assert not mock_loop.called

    # When True, worker task is created
    with patch("app.main.settings.RUN_IN_PROCESS_WORKER", True), \
         patch("app.main.run_ingestion_worker_loop", new_callable=AsyncMock) as mock_loop:
        async with lifespan(fake_app):
            pass
        assert mock_loop.called


@pytest.mark.asyncio
async def test_parsing_offloaded_to_thread():
    """Verify parser.parse and chunking are offloaded via asyncio.to_thread."""
    mock_db = AsyncMock()
    tenant_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_doc = Document(
        id=doc_id,
        tenant_id=tenant_id,
        collection_id=uuid.uuid4(),
        title="Test Document",
        status="queued",
        current_version=1,
    )

    with patch("app.workers.ingestion_worker.DocumentsRepository") as MockDocsRepo, \
         patch("app.workers.ingestion_worker.ChunksRepository") as MockChunksRepo, \
         patch("app.workers.ingestion_worker.asyncio.to_thread", wraps=asyncio.to_thread) as spy_to_thread:

        docs_repo = AsyncMock()
        docs_repo.get_by_id.return_value = mock_doc
        MockDocsRepo.return_value = docs_repo

        chunks_repo = AsyncMock()
        chunks_repo.insert_chunks.return_value = None
        MockChunksRepo.return_value = chunks_repo

        chunk_count = await process_document_pipeline(
            document_id=doc_id,
            tenant_id=tenant_id,
            raw_content=b"Sample document content for offload test",
            filename="sample.txt",
            mime_type="text/plain",
            db=mock_db,
        )

        assert chunk_count >= 1
        # Check that asyncio.to_thread was called for CPU parsing
        assert spy_to_thread.called


def test_ensure_upload_dir_writable_creates_missing_dir():
    """Startup check should create missing upload directory and verify write access."""
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "nested" / "uploads"
        assert not target.exists()
        with patch("app.main.settings.UPLOAD_DIR", str(target)):
            resolved = ensure_upload_dir_writable()
        assert resolved == target
        assert target.is_dir()
        assert list(target.iterdir()) == []


@pytest.mark.asyncio
async def test_lifespan_fails_with_clear_log_when_upload_dir_not_writable():
    """Startup must log a clear error and fail fast if UPLOAD_DIR is not writable."""
    fake_app = MagicMock()
    with tempfile.TemporaryDirectory() as temp_dir:
        blocking_file = Path(temp_dir) / "not_a_dir"
        blocking_file.write_text("occupied", encoding="utf-8")

        with (
            patch("app.main.settings.UPLOAD_DIR", str(blocking_file)),
            patch("app.main.logger") as mock_logger,
            pytest.raises(RuntimeError, match="not writable"),
        ):
            async with lifespan(fake_app):
                pass

        assert mock_logger.critical.called
        log_msg = mock_logger.critical.call_args.args[0]
        assert "not writable" in log_msg.lower()
