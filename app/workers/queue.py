import abc
import json
import logging
from typing import Any
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseIngestionQueue(abc.ABC):
    @abc.abstractmethod
    async def enqueue(self, job_data: dict[str, Any]) -> None:
        pass

    @abc.abstractmethod
    async def dequeue(self, timeout: int = 1) -> dict[str, Any] | None:
        pass

    @abc.abstractmethod
    async def qsize(self) -> int:
        pass


class RedisIngestionQueue(BaseIngestionQueue):
    """
    Redis list-backed FIFO task queue (LPUSH -> BRPOP).
    Provides durable, resilient job dispatching for document ingestion.
    """

    def __init__(self, redis_url: str, queue_name: str | None = None) -> None:
        self.redis_url = redis_url
        self.queue_name = queue_name or settings.INGESTION_QUEUE_NAME
        self._client: aioredis.Redis | None = None

    def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5.0,
            )
        return self._client

    async def enqueue(self, job_data: dict[str, Any]) -> None:
        client = self._get_client()
        serialized = json.dumps(job_data)
        await client.lpush(self.queue_name, serialized)
        logger.info("Enqueued ingestion job to Redis", extra={"job_id": job_data.get("job_id")})

    async def dequeue(self, timeout: int = 1) -> dict[str, Any] | None:
        client = self._get_client()
        try:
            res = await client.brpop(self.queue_name, timeout=timeout)
            if not res:
                return None
            _, item_str = res
            return json.loads(item_str)
        except Exception as e:
            logger.warning(f"Error popping from Redis queue: {e}")
            return None

    async def qsize(self) -> int:
        client = self._get_client()
        try:
            return await client.llen(self.queue_name)
        except Exception:
            return 0


class InMemoryIngestionQueue(BaseIngestionQueue):
    """
    In-memory async FIFO queue for local testing or offline environments.
    """

    def __init__(self) -> None:
        import asyncio
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def enqueue(self, job_data: dict[str, Any]) -> None:
        await self._queue.put(job_data)

    async def dequeue(self, timeout: int = 1) -> dict[str, Any] | None:
        import asyncio
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def qsize(self) -> int:
        return self._queue.qsize()


_global_queue: BaseIngestionQueue | None = None


def get_ingestion_queue() -> BaseIngestionQueue:
    global _global_queue
    if _global_queue is None:
        try:
            _global_queue = RedisIngestionQueue(redis_url=settings.REDIS_URL)
        except Exception as e:
            logger.warning(f"Failed to initialize Redis queue, falling back to InMemory: {e}")
            _global_queue = InMemoryIngestionQueue()
    return _global_queue


def set_ingestion_queue(queue: BaseIngestionQueue | None) -> None:
    global _global_queue
    _global_queue = queue
