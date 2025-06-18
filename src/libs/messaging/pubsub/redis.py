import json
from typing import Callable, Dict, Optional

import structlog

from ....config.redis_adapter import RedisAdapter
from .base import PubSubClient

logger = structlog.get_logger(__name__)

async def create_redis_pubsub(
    host: str = "redis",
    port: int = 6379,
    password: Optional[str] = None,
    cluster_mode: bool = False,
    **kwargs
) -> PubSubClient:
    """
    Create a Redis PubSub client with the given configuration.

    Example:
        # Simple usage with defaults
        pubsub = await create_redis_pubsub()

        # Custom configuration
        pubsub = await create_redis_pubsub(
            host="redis.example.com",
            port=6380,
            password="secret"
        )
    """
    redis_client = RedisAdapter(
        host=host,
        port=port,
        password=password,
        cluster_mode=cluster_mode,
        **kwargs
    )
    await redis_client.initialize()
    return RedisPubSubClient(redis_client.client)

class RedisPubSubClient(PubSubClient):
    """Redis implementation of the PubSub client interface."""

    def __init__(self, redis_client):
        """Initialize the Redis PubSub client with a Redis adapter."""
        self.redis = redis_client
        self._pubsub = None
        self._callbacks = {}

    async def publish(self, channel: str, message: bytes) -> None:
        """Publishes a message to a Redis channel."""
        if self._pubsub is None:
            self._pubsub = self.redis.pubsub()
        try:
            await self.redis.publish(channel, message)
            logger.debug("message_published", channel=channel)
        except Exception as e:
            logger.error("publish_failed", channel=channel, error=str(e))
            raise

    async def subscribe(self, channel: str, callback: Callable[[bytes], None]) -> None:
        """Subscribes to a Redis channel with a callback for messages."""
        if self._pubsub is None:
            self._pubsub = self.redis.pubsub()

        self._callbacks[channel] = callback
        await self._pubsub.subscribe(channel)
        logger.info("subscribed_to_channel", channel=channel)

    async def listen(self) -> None:
        """Listens for messages on subscribed channels."""
        if not self._pubsub:
            logger.warning("no_active_subscriptions")
            return

        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]

                    if channel in self._callbacks:
                        try:
                            await self._callbacks[channel](data)
                        except Exception as e:
                            logger.error(
                                "callback_execution_failed",
                                channel=channel,
                                error=str(e)
                            )
        except Exception as e:
            logger.error("listen_failed", error=str(e))
            raise

    async def close(self) -> None:
        """Closes the pubsub connection."""
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None
            self._callbacks = {}