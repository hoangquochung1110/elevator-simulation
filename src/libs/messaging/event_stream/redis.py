"""
Redis Streams implementation of the Event Stream client interface.
"""
import json
from typing import Any, Dict, List, Optional

import structlog
from redis.asyncio import Redis

from .base import EventStreamClient

logger = structlog.get_logger(__name__)


class RedisStreamClient(EventStreamClient):
    """Redis Streams implementation of the Event Stream client interface."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        **kwargs: Any,
    ):
        """Initialize with Redis connection parameters."""
        self.redis = Redis(
            host=host, port=port, db=db, password=password, decode_responses=True, **kwargs
        )

    async def publish(self, stream: str, data: Dict[str, Any]) -> str:
        """Publish an event to a Redis Stream."""
        try:
            # Convert dict values to strings, bytes, or numbers
            payload = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in data.items()}
            message_id = await self.redis.xadd(stream, payload)
            logger.debug("event_published", stream=stream, message_id=message_id)
            return message_id
        except Exception as e:
            logger.error("publish_failed", stream=stream, error=str(e))
            raise

    async def create_consumer_group(self, stream: str, group: str) -> bool:
        """Create a consumer group for a Redis Stream."""
        try:
            await self.redis.xgroup_create(stream, group, mkstream=True)
            return True
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.warning("consumer_group_exists", stream=stream, group=group)
                return True  # Group already exists
            logger.error("create_group_failed", stream=stream, group=group, error=str(e))
            raise

    async def read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: Optional[int] = None,
        block: Optional[int] = None,
        last_id: str = ">",
    ) -> List[Any]:
        """Read messages from a Redis Stream consumer group."""
        try:
            return await self.redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: last_id},
                count=count,
                block=block,
            )
        except Exception as e:
            logger.error(
                "read_group_failed", stream=stream, group=group, consumer=consumer, error=str(e)
            )
            raise

    async def acknowledge(self, stream: str, group: str, *message_ids: str) -> int:
        """Acknowledge messages in a Redis Stream."""
        if not message_ids:
            return 0
        try:
            return await self.redis.xack(stream, group, *message_ids)
        except Exception as e:
            logger.error(
                "acknowledge_failed",
                stream=stream,
                group=group,
                message_ids=message_ids,
                error=str(e),
            )
            raise

    async def range(self, stream: str, start: str = "-", end: str = "+") -> List[Any]:
        """Retrieve entries from a stream within a given range."""
        try:
            return await self.redis.xrange(stream, start, end)
        except Exception as e:
            logger.error("range_failed", stream=stream, error=str(e))
            raise

    async def trim(
        self,
        stream: str,
        min_id: Optional[str] = None,
        maxlen: Optional[int] = None,
        approximate: bool = True,
    ) -> int:
        """Trim a stream to a certain size."""
        if (min_id is None and maxlen is None) or (
            min_id is not None and maxlen is not None
        ):
            raise ValueError("Provide exactly one of min_id or maxlen")

        try:
            if maxlen is not None:
                return await self.redis.xtrim(
                    stream, maxlen=maxlen, approximate=approximate
                )
            else:
                return await self.redis.xtrim(
                    stream, minid=min_id, approximate=approximate
                )
        except Exception as e:
            logger.error("trim_failed", stream=stream, error=str(e))
            raise

    async def close(self) -> None:
        """Close the Redis connection."""
        await self.redis.close()

    # ... other methods from ABC that need implementation ...
    async def resume_processing(
        self, stream: str, group: str, consumer: str
    ) -> List[Any]:
        logger.warning("resume_processing is not fully implemented yet")
        return []

    async def rebalance_workload(
        self,
        stream: str,
        group: str,
        consumer: str,
        inactive_timeout_ms: int = 30000,
    ) -> List[Any]:
        logger.warning("rebalance_workload is not fully implemented yet")
        return []

    async def get_pending(
        self,
        stream: str,
        group: str,
        consumer: Optional[str] = None,
        count: Optional[int] = None,
    ) -> List[Any]:
        logger.warning("get_pending is not fully implemented yet")
        return []

    async def claim_pending(
        self,
        stream: str,
        group: str,
        consumer: str,
        min_idle_time: int,
        *message_ids: str,
    ) -> List[Any]:
        logger.warning("claim_pending is not fully implemented yet")
        return []

    async def stream_info(self, stream: str) -> Any:
        logger.warning("stream_info is not fully implemented yet")
        return None