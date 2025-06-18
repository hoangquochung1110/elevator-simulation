"""Redis Pub/Sub client implementation.

This module provides a Redis-based implementation of the PubSubClient interface.
"""
import json
import logging
from typing import Any, AsyncIterator, Dict, Optional, Union

from redis.asyncio.client import PubSub as RedisPubSub
from redis.exceptions import ConnectionError as RedisConnectionError

from ....config.redis_adapter import RedisAdapter
from .base import PubSubClient

logger = logging.getLogger(__name__)


async def create_redis_pubsub(
    host: str = "redis",
    port: int = 6379,
    password: Optional[str] = None,
    cluster_mode: bool = False,
    **kwargs
) -> 'RedisPubSubClient':
    """Create a Redis Pub/Sub client with the given configuration.

    Args:
        host: Redis host or list of cluster nodes.
        port: Redis port.
        password: Redis password.
        cluster_mode: Whether to use cluster mode.
        **kwargs: Additional Redis client arguments.

    Returns:
        An instance of RedisPubSubClient.
    """
    redis_adapter = RedisAdapter(
        host=host,
        port=port,
        password=password,
        cluster_mode=cluster_mode,
        **kwargs
    )
    await redis_adapter.initialize()
    return RedisPubSubClient(redis_adapter.client)


class RedisPubSubClient(PubSubClient):
    """Redis implementation of the PubSubClient interface.

    This class provides a high-level interface for Redis Pub/Sub operations
    with support for both single instance and cluster deployments.
    """

    def __init__(self, redis_client):
        """Initialize the Redis Pub/Sub client.

        Args:
            redis_client: An instance of RedisAdapter.
        """
        self.redis = redis_client
        self._pubsub: Optional[RedisPubSub] = None
        self._subscriptions = set()

    async def _ensure_connected(self) -> None:
        """Ensure the Pub/Sub connection is established."""
        if self._pubsub is None:
            self._pubsub = self.redis.pubsub()

    async def publish(self, channel: str, message: Union[str, Dict[str, Any]]) -> None:
        """Publish a message to a channel.

        Args:
            channel: The channel to publish to.
            message: The message to publish. Can be a string or a dictionary.
        """

        try:
            msg = json.dumps(message) if isinstance(message, dict) else str(message)
            await self.redis.publish(channel, msg)
            logger.debug("Published message to channel", channel=channel, message=msg)
        except RedisConnectionError as e:
            logger.error("Failed to publish message", channel=channel, error=str(e))
            raise

    async def subscribe(self, channel: str) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to a channel and yield messages as they arrive.

        Args:
            channel: The channel to subscribe to.

        Yields:
            Messages received on the channel as dictionaries.
        """
        await self._ensure_connected()
        assert self._pubsub is not None  # For type checking

        if channel not in self._subscriptions:
            await self._pubsub.subscribe(channel)
            self._subscriptions.add(channel)
            logger.debug("Subscribed to channel", channel=channel)

        try:
            while True:
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["channel"].decode() == channel:
                    try:
                        data = json.loads(message["data"])
                        if isinstance(data, dict):
                            yield data
                    except json.JSONDecodeError:
                        yield {"data": message["data"].decode()}
        except Exception as e:
            logger.error("Error in subscription", channel=channel, error=str(e))
            raise

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel.

        Args:
            channel: The channel to unsubscribe from.
        """
        if self._pubsub is not None and channel in self._subscriptions:
            await self._pubsub.unsubscribe(channel)
            self._subscriptions.discard(channel)
            logger.debug("Unsubscribed from channel", channel=channel)

    async def close(self) -> None:
        """Close the client and release any resources."""
        if self._pubsub is not None:
            # Unsubscribe from all channels
            if self._subscriptions:
                await self._pubsub.unsubscribe(*self._subscriptions)
                self._subscriptions.clear()
            await self._pubsub.close()
            self._pubsub = None
            logger.debug("Closed Redis Pub/Sub client")
