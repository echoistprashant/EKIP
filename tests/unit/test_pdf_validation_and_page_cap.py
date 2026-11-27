import io
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile
from pypdf import PdfWriter
from starlette.datastructures import Headers

from app.models.collection import Collection
from app.models.user import User
from app.rag.parsing.pdf import PDFParser
from app.services.ingestion_service import IngestionService


def create_dummy_pdf(num_pages: int = 1) -> bytes:
    """Helper to generate a synthetically valid in-memory PDF with N pages."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_pdf_magic_bytes_parser_rejection():
    """PDFParser must reject files that do not start with %PDF-."""
    parser = PDFParser()
    fake_content = b"<html><body>Not a PDF</body></html>"
    with pytest.raises(ValueError) as exc:
        parser.parse(fake_content, "fake.pdf")
    assert "Missing %PDF- magic bytes" in str(exc.value)


def test_pdf_page_ceiling_parser_rejection():
    """PDFParser must reject PDFs that exceed 100 pages."""
    parser = PDFParser()
    large_pdf = create_dummy_pdf(num_pages=105)
    with pytest.raises(ValueError) as exc:
        parser.parse(large_pdf, "large.pdf")
    assert "100 pages" in str(exc.value)


@pytest.mark.asyncio
async def test_ingestion_rejects_fake_pdf_magic_bytes():
    """
    IngestionService must check magic bytes instead of trusting content_type or extension.
    A fake PDF must be rejected with HTTP 400.
    """
    fake_pdf = UploadFile(
        filename="disguised.pdf",
        file=io.BytesIO(b"MALICIOUS_NON_PDF_PAYLOAD"),
        headers=Headers({"content-type": "application/pdf"}),
    )

    mock_db = AsyncMock()
    mock_cols_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    collection_id = uuid.uuid4()
    mock_cols_repo.get_by_id.return_value = Collection(
        id=collection_id, tenant_id=tenant_id, name="Test Col"
    )
    mock_docs_repo = AsyncMock()
    mock_docs_repo.get_by_hash.return_value = None

    service = IngestionService(mock_db)
    service.cols_repo = mock_cols_repo
    service.docs_repo = mock_docs_repo
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email="u@test.com", role="admin")

    with pytest.raises(HTTPException) as exc:
        await service.ingest_file(
            file=fake_pdf,
            collection_id=collection_id,
            user=user,
            async_mode=True,
        )

    assert exc.value.status_code == 400
    assert "Missing %PDF- magic bytes signature" in exc.value.detail


@pytest.mark.asyncio
async def test_ingestion_rejects_pdf_over_100_pages():
    """
    IngestionService must cap PDFs at 100 pages and reject 101+ page PDFs with HTTP 400.
    """
    pdf_101_pages = create_dummy_pdf(num_pages=101)
    upload = UploadFile(
        filename="oversized.pdf",
        file=io.BytesIO(pdf_101_pages),
        headers=Headers({"content-type": "application/pdf"}),
    )

    mock_db = AsyncMock()
    mock_cols_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    collection_id = uuid.uuid4()
    mock_cols_repo.get_by_id.return_value = Collection(
        id=collection_id, tenant_id=tenant_id, name="Test Col"
    )
    mock_docs_repo = AsyncMock()
    mock_docs_repo.get_by_hash.return_value = None

    service = IngestionService(mock_db)
    service.cols_repo = mock_cols_repo
    service.docs_repo = mock_docs_repo
    user = User(id=uuid.uuid4(), tenant_id=tenant_id, email="u@test.com", role="admin")

    with pytest.raises(HTTPException) as exc:
        await service.ingest_file(
            file=upload,
            collection_id=collection_id,
            user=user,
            async_mode=True,
        )

    assert exc.value.status_code == 400
    assert "exceeds maximum allowed limit of 100 pages" in exc.value.detail
