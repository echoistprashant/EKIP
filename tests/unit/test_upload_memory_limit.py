import io
import uuid
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, UploadFile
import pytest

from app.models.collection import Collection
from app.models.user import User
from app.services.ingestion_service import (
    MAX_FILE_SIZE_BYTES,
    UPLOAD_CHUNK_SIZE_BYTES,
    IngestionService,
)


class ChunkedMockUploadFile(UploadFile):
    """
    Simulates a streaming UploadFile that tracks chunk reads
    and can simulate arbitrarily large files without allocating memory.
    """
    def __init__(self, total_size: int, chunk_size: int = UPLOAD_CHUNK_SIZE_BYTES):
        super().__init__(filename="large_file.txt", file=io.BytesIO())
        self.total_size = total_size
        self.bytes_read = 0
        self.read_calls = 0

    async def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if self.bytes_read >= self.total_size:
            return b""
        remaining = self.total_size - self.bytes_read
        to_read = min(remaining, size if size > 0 else remaining)
        self.bytes_read += to_read
        return b"A" * to_read


@pytest.mark.asyncio
async def test_upload_exceeding_50mb_rejected_with_413():
    """
    Verify that an upload exceeding 50 MB is immediately rejected with HTTP 413
    after reading in 64 KB chunks, without reading the remaining stream into memory.
    """
    # 52 MB stream
    total_size = 52 * 1024 * 1024
    streaming_file = ChunkedMockUploadFile(total_size=total_size)

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_cols_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    collection_id = uuid.uuid4()
    mock_cols_repo.get_by_id.return_value = Collection(
        id=collection_id, tenant_id=tenant_id, name="Test Col"
    )

    service = IngestionService(mock_db)
    service.cols_repo = mock_cols_repo
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email="u@test.com", role="admin")

    with pytest.raises(HTTPException) as exc_info:
        await service.ingest_file(
            file=streaming_file,
            collection_id=collection_id,
            user=user,
            async_mode=True,
        )

    assert exc_info.value.status_code == 413
    assert "50 MB" in exc_info.value.detail or "50" in exc_info.value.detail

    # Crucial assertion: Server stopped reading immediately when 50 MB was exceeded!
    # Expected read calls = (50 MB // 64 KB) + 1 = 801 calls
    assert streaming_file.bytes_read < total_size
    assert streaming_file.bytes_read <= MAX_FILE_SIZE_BYTES + UPLOAD_CHUNK_SIZE_BYTES


@pytest.mark.asyncio
async def test_upload_within_limit_success():
    """Verify upload under 50 MB reads all chunks properly."""
    content = b"X" * (128 * 1024)  # 128 KB
    file = UploadFile(filename="small.txt", file=io.BytesIO(content))

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_cols_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    collection_id = uuid.uuid4()
    mock_cols_repo.get_by_id.return_value = Collection(
        id=collection_id, tenant_id=tenant_id, name="Test Col"
    )
    mock_docs_repo = AsyncMock()
    mock_docs_repo.get_by_hash.return_value = None
    mock_docs_repo.create.side_effect = lambda doc: doc

    service = IngestionService(mock_db)
    service.cols_repo = mock_cols_repo
    service.docs_repo = mock_docs_repo
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email="u@test.com", role="admin")

    doc, _, _ = await service.ingest_file(
        file=file,
        collection_id=collection_id,
        user=user,
        async_mode=True,
    )
    assert doc is not None
