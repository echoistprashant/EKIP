import abc
from datetime import datetime, timezone
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

    @abc.abstractmethod
    async def enqueue_dlq(self, job_data: dict[str, Any], error: str) -> None:
        pass

    @abc.abstractmethod
    async def dequeue_dlq(self, timeout: int = 1) -> dict[str, Any] | None:
        pass

    @abc.abstractmethod
    async def dlq_size(self) -> int:
        pass


class RedisIngestionQueue(BaseIngestionQueue):
    """
    Redis list-backed FIFO task queue (LPUSH -> BRPOP).
    Provides durable, resilient job dispatching for document ingestion with DLQ support.
    """

    def __init__(
        self,
        redis_url: str,
        queue_name: str | None = None,
        dlq_name: str | None = None,
    ) -> None:
        self.redis_url = redis_url
        self.queue_name = queue_name or settings.INGESTION_QUEUE_NAME
        self.dlq_name = dlq_name or settings.INGESTION_DLQ_NAME
        self._client: aioredis.Redis | None = None

    def _get_client(self) -> aioredis.Redis:
        import asyncio
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._client is not None:
            client_loop = getattr(self, "_client_loop", None)
            if client_loop is not None and (client_loop.is_closed() or client_loop != current_loop):
                self._client = None

        if self._client is None:
            self._client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5.0,
            )
            self._client_loop = current_loop
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

    async def enqueue_dlq(self, job_data: dict[str, Any], error: str) -> None:
        client = self._get_client()
        dlq_item = dict(job_data)
        dlq_item["dlq_error"] = error
        dlq_item["dlq_at"] = datetime.now(timezone.utc).isoformat()
        serialized = json.dumps(dlq_item)
        await client.lpush(self.dlq_name, serialized)
        logger.error(
            "Enqueued failed job to Dead-Letter Queue (DLQ)",
            extra={"job_id": job_data.get("job_id"), "dlq": self.dlq_name, "error": error},
        )

    async def dequeue_dlq(self, timeout: int = 1) -> dict[str, Any] | None:
        client = self._get_client()
        try:
            res = await client.brpop(self.dlq_name, timeout=timeout)
            if not res:
                return None
            _, item_str = res
            return json.loads(item_str)
        except Exception as e:
            logger.warning(f"Error popping from DLQ: {e}")
            return None

    async def dlq_size(self) -> int:
        client = self._get_client()
        try:
            return await client.llen(self.dlq_name)
        except Exception:
            return 0


class InMemoryIngestionQueue(BaseIngestionQueue):
    """
    In-memory async FIFO queue for local testing or offline environments.
    """

    def __init__(self) -> None:
        import asyncio
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._dlq: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

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

    async def enqueue_dlq(self, job_data: dict[str, Any], error: str) -> None:
        dlq_item = dict(job_data)
        dlq_item["dlq_error"] = error
        dlq_item["dlq_at"] = datetime.now(timezone.utc).isoformat()
        await self._dlq.put(dlq_item)

    async def dequeue_dlq(self, timeout: int = 1) -> dict[str, Any] | None:
        import asyncio
        try:
            return await asyncio.wait_for(self._dlq.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def dlq_size(self) -> int:
        return self._dlq.qsize()


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
