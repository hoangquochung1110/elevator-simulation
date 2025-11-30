"""
Redis Streams implementation of the Event Stream client interface.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, cast

from redis.asyncio import Redis

from .base import EventStreamClient

logger = logging.getLogger(__name__)


class RedisStreamClient(EventStreamClient):
    """Redis Streams implementation of the Event Stream client interface."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: int = 0,
        password: Optional[str] = None,
        **kwargs: Any,
    ):
        """Initialize with Redis connection parameters."""
        redis_host = host or os.environ.get("REDIS_HOST", "localhost")
        redis_port = port or int(os.environ.get("REDIS_PORT", 6379))
        self.redis = Redis(
            host=redis_host,
            port=redis_port,
            db=db,
            password=password,
            decode_responses=True,
            **kwargs,
        )

    async def publish(self, stream: str, data: Dict[str, Any]) -> str:
        """Publish an event to a Redis Stream."""
        try:
            # Normalize values to encodable types accepted by redis: str, bytes, int, float
            payload: Dict[str, Any] = {}
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    payload[k] = json.dumps(v)
                elif isinstance(v, (str, bytes, int, float)):
                    payload[k] = v
                elif v is None:
                    payload[k] = ""
                else:
                    try:
                        payload[k] = json.dumps(v)
                    except TypeError:
                        payload[k] = str(v)
            message_id = await self.redis.xadd(
                stream, cast(Dict[Any, Any], payload)
            )
            logger.debug(
                "Event published to stream '%s' with message ID: %s",
                stream,
                message_id,
            )
            return message_id
        except Exception as e:
            logger.error(
                "Failed to publish to stream '%s': %s", stream, str(e)
            )
            raise

    async def create_consumer_group(
        self, stream: str, group: str, start_id: str = "$"
    ) -> bool:
        """Create a consumer group for a stream."""
        try:
            await self.redis.xgroup_create(
                stream, group, start_id, mkstream=True
            )
            logger.debug(
                "Created consumer group '%s' for stream '%s' starting at ID '%s'",
                group,
                stream,
                start_id,
            )
            return True
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.warning(
                    "Consumer group '%s' already exists for stream '%s'",
                    group,
                    stream,
                )
                return True  # Group already exists
            logger.error(
                "Failed to create consumer group '%s' for stream '%s': %s",
                group,
                stream,
                str(e),
            )
            return False

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
                "Failed to read from group '%s' on stream '%s' for consumer '%s': %s",
                group,
                stream,
                consumer,
                str(e),
            )
            raise

    async def acknowledge(
        self, stream: str, group: str, *message_ids: str
    ) -> int:
        """Acknowledge messages in a Redis Stream."""
        if not message_ids:
            return 0
        try:
            return await self.redis.xack(stream, group, *message_ids)
        except Exception as e:
            logger.error(
                "Failed to acknowledge messages %s in group '%s' on stream '%s': %s",
                message_ids,
                group,
                stream,
                str(e),
            )
            raise

    async def range(
        self, stream: str, start: str = "-", end: str = "+"
    ) -> List[Any]:
        """Retrieve entries from a stream within a given range."""
        try:
            return await self.redis.xrange(stream, start, end)
        except Exception as e:
            logger.error(
                "Failed to retrieve range from stream '%s': %s", stream, str(e)
            )
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
            logger.error("Failed to trim stream '%s': %s", stream, str(e))
            raise

    async def close(self) -> None:
        """Close the Redis connection."""
        await self.redis.close()

    async def resume_processing(
        self, stream: str, group: str, consumer: str
    ) -> List[Any]:
        logger.warning("Resume processing is not fully implemented yet")
        return []

    async def rebalance_workload(
        self,
        stream: str,
        group: str,
        consumer: str,
        inactive_timeout_ms: int = 30000,
    ) -> List[Any]:
        logger.warning("Rebalance workload is not fully implemented yet")
        return []

    async def get_pending(
        self,
        stream: str,
        group: str,
        consumer: Optional[str] = None,
        count: Optional[int] = None,
    ) -> List[Any]:
        logger.warning("Get pending is not fully implemented yet")
        return []

    async def claim_pending(
        self,
        stream: str,
        group: str,
        consumer: str,
        min_idle_time: int,
        *message_ids: str,
    ) -> List[Any]:
        logger.warning("Claim pending is not fully implemented yet")
        return []

    async def stream_info(self, stream: str) -> Any:
        logger.warning("Stream info is not fully implemented yet")
        return None
