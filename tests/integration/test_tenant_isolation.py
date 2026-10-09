import uuid
import pytest
from app.models.tenant import Tenant
from app.models.collection import Collection
from app.models.document import Document
from app.models.chunk import Chunk
from app.repositories.chunks_repo import ChunksRepository


@pytest.mark.asyncio
async def test_tenant_cannot_read_another_tenants_chunks(db_session):
    repo = ChunksRepository(db_session)

    # 1. Tenant A and Tenant B create karo
    unique_suffix = uuid.uuid4().hex[:8]
    tenant_a = Tenant(name=f"Tenant-A-{unique_suffix}")
    tenant_b = Tenant(name=f"Tenant-B-{unique_suffix}")
    db_session.add_all([tenant_a, tenant_b])
    await db_session.flush()

    # 2. Tenant A ke liye Collection, Document aur Chunk create karo
    col_a = Collection(tenant_id=tenant_a.id, name="HR Confidential")
    db_session.add(col_a)
    await db_session.flush()

    doc_a = Document(
        tenant_id=tenant_a.id,
        collection_id=col_a.id,
        title="Salaries Policy",
        mime_type="application/pdf",
        content_hash=f"hash_{unique_suffix}",
        storage_key=f"s3://docs/{unique_suffix}.pdf",
    )
    db_session.add(doc_a)
    await db_session.flush()

    chunk_a = Chunk(
        tenant_id=tenant_a.id,
        collection_id=col_a.id,
        document_id=doc_a.id,
        ordinal=0,
        content="Confidential executive compensation data of Tenant A.",
        token_count=12,
        embedding=[0.0] * 1024,
        embedding_model="text-embedding-3-large",
    )
    await repo.insert_chunks([chunk_a])

    # 3. Tenant A retrieves its own chunk -> SUCCESS
    retrieved_a = await repo.get_by_id(chunk_a.id, tenant_id=tenant_a.id)
    assert retrieved_a is not None
    assert retrieved_a.content == "Confidential executive compensation data of Tenant A."

    # 4. THE ATTACK: Tenant B tries to query Tenant A's chunk by ID
    leaked_chunk = await repo.get_by_id(chunk_a.id, tenant_id=tenant_b.id)

    # 5. ASSERTION: Zero Data Leakage - Tenant B gets None
    assert leaked_chunk is None
