import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

import os
from ....config import get_redis_client, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB
from .base import EventStreamClient

logger = structlog.get_logger(__name__)


async def create_redis_stream(
    redis_client=None,
    **kwargs
):
    """
    Create a Redis Stream client with the given configuration.
    
    Args:
        redis_client: Existing Redis client to use (recommended)
        **kwargs: Additional Redis client arguments (ignored if redis_client is provided)
        
    Returns:
        RedisStreamClient instance
    """
    if redis_client is None:
        redis_client = await get_redis_client(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD
        )
        
    return RedisStreamClient(redis_client)


class RedisStreamClient(EventStreamClient):
    """Redis Streams implementation of the Event Stream client interface."""

    def __init__(self, redis_client):
        """Initialize with a Redis adapter."""
        super().__init__()
        self.redis = redis_client

    async def resume_processing(self, stream, group, consumer):
        """Resume processing from where this consumer left off."""
        messages = []

        try:
            # 1. First, read pending messages for this specific consumer
            pending = await self.redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: "0"},  # '0' means all pending messages
                count=100  # Limit batch size
            )

            if pending:
                for stream_name, stream_messages in pending:
                    for msg_id, msg_data in stream_messages:
                        messages.append({
                            'id': msg_id,
                            'data': msg_data,
                            'stream': stream_name,
                            'timestamp': datetime.fromtimestamp(int(msg_id.split("-")[0]) / 1000)
                        })

            # 2. Then read new messages
            new_messages = await self.redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},  # '>' means new messages only
                count=100,
                block=0  # Don't block if no new messages
            )

            if new_messages:
                for stream_name, stream_messages in new_messages:
                    for msg_id, msg_data in stream_messages:
                        messages.append({
                            'id': msg_id,
                            'data': msg_data,
                            'stream': stream_name,
                            'timestamp': datetime.fromtimestamp(int(msg_id.split("-")[0]) / 1000)
                        })

            return messages

        except Exception as e:
            logger.error(
                "resume_processing_failed",
                stream=stream,
                group=group,
                consumer=consumer,
                error=str(e)
            )
            raise

    async def rebalance_workload(
        self,
        stream: str,
        group: str,
        consumer: str,
        inactive_timeout_ms: int = 30000
    ):
        """Claim and process messages from inactive consumers."""
        try:
            # 1. Get information about pending messages in the group
            pending_info = await self.redis.client.xpending_range(
                stream,
                group,
                min="-",
                max="+",
                count=100
            )

            if not pending_info:
                return []

            # 2. Find messages that have been idle too long
            claimable_ids = [
                entry["message_id"]
                for entry in pending_info
                if entry["time_since_delivered"] >= inactive_timeout_ms
                and entry["consumer"] != consumer  # Don't claim our own messages
            ]

            if not claimable_ids:
                return []

            # 3. Claim messages from inactive consumers
            claimed = await self.redis.client.xclaim(
                stream,
                group,
                consumer,
                min_idle_time=inactive_timeout_ms,
                messages=claimable_ids
            )

            # 4. Convert to message format
            return [
                {
                    'id': msg_id,
                    'data': msg_data[b'data'],
                    'stream': stream,
                    'timestamp': datetime.fromtimestamp(int(msg_id.split("-")[0]) / 1000)
                }
                for msg_id, msg_data in claimed
            ]

        except Exception as e:
            logger.error(
                "rebalance_workload_failed",
                stream=stream,
                group=group,
                consumer=consumer,
                error=str(e)
            )
            raise

    async def publish(self, stream: str, data: Dict[str, Any]) -> str:
        """Publish an event to a Redis Stream."""
        # try:
        #     # Store the entire dictionary as a JSON string under the 'data' field
        #     message_id = await self.redis.xadd(stream, {'data': json.dumps(data)})
        #     logger.debug("event_published", stream=stream, message_id=message_id)
        #     return message_id
        # except Exception as e:
        #     logger.error("publish_failed", stream=stream, error=str(e))
        #     raise
        try:
            # Convert data to bytes if it's a string
            if isinstance(data, str):
                data = data.encode('utf-8')
            elif isinstance(data, dict):
                data = {k: v if isinstance(v, (bytes, bytearray, memoryview))
                       else str(v).encode('utf-8') for k, v in data.items()}

            message_id = await self.redis.xadd(stream, data)
            logger.debug("event_published", stream=stream, message_id=message_id)
            return message_id
        except Exception as e:
            logger.error("publish_failed", stream=stream, error=str(e))
            raise

    async def create_consumer_group(
        self,
        stream: str,
        group: str,
    ) -> bool:
        """Create a consumer group for a Redis Stream."""
        try:
            return await self.redis.xgroup_create(
                stream,
                group,
                mkstream=True
            )
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.error(
                    "busy_group",
                    stream=stream,
                    group=group,
                    error=str(e)
                )
                return False
            logger.error(
                "create_group_failed",
                stream=stream,
                group=group,
                error=str(e)
            )
            raise

    async def read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: Optional[int] = None,
        block: Optional[int] = None,
        last_id: str = ">"
    ):
        """Read messages from a Redis Stream consumer group."""
        try:
            results = await self.redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: last_id},
                count=count,
                block=block
            )
            return results

        except Exception as e:
            logger.error(
                "read_group_failed",
                stream=stream,
                group=group,
                consumer=consumer,
                error=str(e)
            )
            raise

    async def acknowledge(
        self,
        stream: str,
        group: str,
        *message_ids: str
    ) -> int:
        """Acknowledge messages in a Redis Stream."""
        if not message_ids:
            return 0

        try:
            logger.info(
                "acknowledged",
                stream=stream,
                group=group,
                message_ids=message_ids,
            )
            return await self.redis.xack(stream, group, *message_ids)
        except Exception as e:
            logger.error(
                "acknowledge_failed",
                stream=stream,
                group=group,
                message_ids=message_ids,
                error=str(e)
            )
            raise

    async def get_pending(
        self,
        stream: str,
        group: str,
        consumer: Optional[str] = None,
        count: Optional[int] = None
    ):
        """Get pending messages from a Redis Stream consumer group."""
        try:
            # Get pending messages info
            pending = await self.redis.client.xpending(stream, group)
            if not pending:
                return []

            # Get detailed pending messages
            messages = []
            pending_ids = await self.redis.client.xpending_range(
                stream,
                group,
                min="-",
                max="+",
                count=count or pending["pending"]
            )

            for p in pending_ids:
                msg = await self.redis.client.xrange(
                    stream,
                    min=p["message_id"],
                    max=p["message_id"]
                )
                if msg:
                    msg_id, msg_data = msg[0]
                    messages.append({
                        'id': msg_id,
                        'data': msg_data,
                        'stream': stream,
                        'timestamp': datetime.fromtimestamp(int(msg_id.split("-")[0]) / 1000),
                        'consumer': p["consumer"],
                        'delivery_time': datetime.fromtimestamp(p["last_delivered_ms"] / 1000),
                        'delivery_count': p["times_delivered"]
                    })
            return messages

        except Exception as e:
            logger.error(
                "get_pending_failed",
                stream=stream,
                group=group,
                error=str(e)
            )
            raise

    async def claim_pending(
        self,
        stream: str,
        group: str,
        consumer: str,
        min_idle_time: int,
        *message_ids: str
    ):
        """Claim pending messages in a Redis Stream."""
        if not message_ids:
            return []

        try:
            claimed = await self.redis.client.xclaim(
                stream,
                group,
                consumer,
                min_idle_time,
                message_ids
            )

            messages = []
            for msg_id, msg_data in claimed:
                messages.append({
                    'id': msg_id,
                    'data': msg_data,
                    'stream': stream,
                    'timestamp': datetime.fromtimestamp(int(msg_id.split("-")[0]) / 1000)
                })
            return messages

        except Exception as e:
            logger.error(
                "claim_pending_failed",
                stream=stream,
                group=group,
                consumer=consumer,
                error=str(e)
            )
            raise

    async def stream_info(self, stream):
        """Get information about a Redis Stream."""
        try:
            info = await self.redis.client.xinfo_stream(stream)
            return {
                'length': info['length'],
                "radix_tree_keys": info["radix-tree-keys"],
                "radix_tree_nodes": info["radix-tree-nodes"],
                "groups": info["groups"],
                "last_generated_id": info["last-generated-id"],
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
            }
        except Exception as e:
            logger.error("stream_info_failed", stream=stream, error=str(e))
            raise

    async def close(self) -> None:
        """Close the Redis connection."""
        await self.redis.close()


    async def range(self, stream, start="-", end="+"):
        entries = await self.redis.xrange(stream, start, end)
        return entries

    async def trim(self, stream, min_id=None, maxlen=None, approximate=True):
        # TODO: Need enforce exclusive parameters
        if maxlen is not None:
            trimmed_count = await self.redis.xtrim(
                stream,
                maxlen=maxlen,
                approximate=approximate,
            )
        else:
            # Trim by ID
            trimmed_count = await self.redis.xtrim(
                stream,
                minid=min_id,
                approximate=approximate,
            )
        return trimmed_count
