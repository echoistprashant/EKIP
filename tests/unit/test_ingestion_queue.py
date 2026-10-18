import io
import uuid
import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.job import IngestionJob
from app.models.tenant import Tenant
from app.models.user import User
from app.models.collection import Collection
from app.workers.queue import InMemoryIngestionQueue, RedisIngestionQueue
from app.workers.worker import IngestionWorker


@pytest.mark.asyncio
async def test_inmemory_queue_operations():
    q = InMemoryIngestionQueue()
    assert await q.qsize() == 0

    item = {"job_id": str(uuid.uuid4()), "action": "ingest"}
    await q.enqueue(item)
    assert await q.qsize() == 1

    popped = await q.dequeue(timeout=1)
    assert popped == item
    assert await q.qsize() == 0


@pytest.mark.asyncio
async def test_redis_queue_live_operations():
    from app.core.config import settings
    queue_name = f"test:queue:{uuid.uuid4().hex[:8]}"
    q = RedisIngestionQueue(redis_url=settings.REDIS_URL, queue_name=queue_name)

    item = {"job_id": str(uuid.uuid4()), "payload": "sample_data"}
    await q.enqueue(item)
    assert await q.qsize() >= 1

    popped = await q.dequeue(timeout=2)
    assert popped is not None
    assert popped["job_id"] == item["job_id"]
    assert popped["payload"] == "sample_data"
