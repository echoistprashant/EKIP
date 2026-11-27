import io
from pathlib import Path
import tempfile
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
import pytest

from app.core.config import settings
from app.models.collection import Collection
from app.models.user import User
from app.services.ingestion_service import IngestionService, sanitize_filename


def test_sanitize_filename_path_traversal():
    """
    Test that filenames containing directory traversal characters
    are sanitized using Path(name).name and a safe-character regex.
    """
    # 1. POSIX traversal payload
    assert sanitize_filename("../../etc/passwd") == "passwd"

    # 2. Windows traversal payload
    assert sanitize_filename(r"..\..\x.bat") == "x.bat"

    # 3. Deep relative traversal
    assert sanitize_filename("../../../../Windows/System32/cmd.exe") == "cmd.exe"
    assert sanitize_filename(r"..\..\..\..\boot.ini") == "boot.ini"

    # 4. Special characters replaced by safe regex
    sanitized_special = sanitize_filename("../../my document (confidential) [v1].pdf")
    assert "/" not in sanitized_special
    assert "\\" not in sanitized_special
    assert ".." not in sanitized_special
    assert sanitized_special.endswith(".pdf")

    # 5. Empty or pure traversal dots fallback
    assert sanitize_filename(None) == "uploaded_document"
    assert sanitize_filename("") == "uploaded_document"
    assert sanitize_filename("../..") == "uploaded_document"


@pytest.mark.asyncio
async def test_ingest_file_staged_path_safety():
    """
    Test that IngestionService writes uploaded files strictly inside
    the tenant's upload directory even with traversal filenames.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        orig_upload_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = temp_dir
        try:
            tenant_id = uuid.uuid4()
            user = User(id=uuid.uuid4(), tenant_id=tenant_id, email="test@example.com", role="admin")
            collection_id = uuid.uuid4()

            mock_db = AsyncMock()
            mock_db.add = MagicMock()
            mock_cols_repo = AsyncMock()
            mock_cols_repo.get_by_id.return_value = Collection(
                id=collection_id, tenant_id=tenant_id, name="Test Col"
            )
            mock_docs_repo = AsyncMock()
            mock_docs_repo.get_by_hash.return_value = None
            mock_docs_repo.create.side_effect = lambda doc: doc

            service = IngestionService(mock_db)
            service.cols_repo = mock_cols_repo
            service.docs_repo = mock_docs_repo

            with patch("app.services.ingestion_service.get_ingestion_queue") as mock_get_q:
                mock_get_q.return_value = AsyncMock()

                # Test with ../../etc/passwd
                upload1 = UploadFile(
                    filename="../../etc/passwd",
                    file=io.BytesIO(b"dummy file content for traversal test"),
                )
                doc1, _, _ = await service.ingest_file(
                    file=upload1,
                    collection_id=collection_id,
                    user=user,
                    async_mode=True,
                )

                expected_dir = Path(temp_dir) / str(tenant_id)
                assert Path(doc1.storage_key).resolve().is_relative_to(expected_dir.resolve())
                assert Path(doc1.storage_key).name.endswith("_passwd")

                # Test with ..\..\x.bat
                upload2 = UploadFile(
                    filename=r"..\..\x.bat",
                    file=io.BytesIO(b"echo batch file content"),
                )
                doc2, _, _ = await service.ingest_file(
                    file=upload2,
                    collection_id=collection_id,
                    user=user,
                    async_mode=True,
                )

                assert Path(doc2.storage_key).resolve().is_relative_to(expected_dir.resolve())
                assert Path(doc2.storage_key).name.endswith("_x.bat")

        finally:
            settings.UPLOAD_DIR = orig_upload_dir
