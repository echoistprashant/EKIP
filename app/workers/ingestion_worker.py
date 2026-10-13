import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document
from app.rag.chunking.structural import StructuralChunker
from app.rag.cleaning import document_cleaner
from app.rag.parsing.registry import parser_registry
from app.repositories.chunks_repo import ChunksRepository
from app.repositories.documents_repo import DocumentsRepository

logger = logging.getLogger("ekip.ingestion_worker")


async def process_document_pipeline(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID,
    raw_content: bytes,
    filename: str,
    mime_type: str,
    db: AsyncSession,
) -> int:
    """
    Core Ingestion pipeline worker:
    1. Parse bytes into structured Elements
    2. Clean repetitive headers/footers
    3. Structural chunking with Contextual Headers
    4. Atomic batch insertion of Chunks into PostgreSQL
    5. Update Document status to 'indexed'
    """
    docs_repo = DocumentsRepository(db)
    chunks_repo = ChunksRepository(db)

    doc = await docs_repo.get_by_id(document_id, tenant_id)
    if not doc:
        raise ValueError(f"Document {document_id} not found for tenant {tenant_id}")

    try:
        # Update status to processing
        doc.status = "processing"
        await db.flush()

        # Step 1: Parse
        parser = parser_registry.get_parser(mime_type, filename)
        elements = parser.parse(raw_content, filename)

        # Step 2: Clean
        cleaned_elements = document_cleaner.clean(elements)

        # Step 3: Chunk
        chunker = StructuralChunker(max_tokens=400, overlap_tokens=50)
        chunks_data = chunker.chunk(cleaned_elements, doc.title)

        # Step 4: Convert to DB Chunk models
        # Note: Vector embeddings will be calculated in Phase 5.
        # Storing placeholder 1024-d zero vector to satisfy NOT NULL HNSW schema constraint.
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
                embedding=[0.0] * 1024,
                embedding_model="pending",
            )
            for c in chunks_data
        ]

        # Step 5: Persist Chunks and update status
        await chunks_repo.insert_chunks(db_chunks)
        doc.status = "indexed"
        doc.error_code = None
        await db.commit()

        logger.info(
            "Document ingestion completed",
            extra={"document_id": str(doc.id), "chunk_count": len(db_chunks)},
        )
        return len(db_chunks)

    except Exception as e:
        await db.rollback()
        doc.status = "failed"
        doc.error_code = str(e)[:100]
        await db.commit()
        logger.error(f"Document ingestion failed: {e}", exc_info=True)
        raise
