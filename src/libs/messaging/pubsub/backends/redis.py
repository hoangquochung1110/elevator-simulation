"""Redis Pub/Sub client implementation."""

import os
import json
import logging
from typing import Any, Dict, Optional, Union

from redis.asyncio import Redis
from redis.asyncio.client import PubSub as RedisPubSub
from redis.exceptions import ConnectionError as RedisConnectionError

from ..base import PubSubClient
from ..exceptions import PubSubConnectionError, PubSubPublishError

logger = logging.getLogger(__name__)


class RedisPubSubBackend(PubSubClient):
    """Redis implementation of the PubSubClient interface."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: int = 0,
        password: Optional[str] = None,
        **kwargs: Any,
    ):
        """Initialize with Redis connection parameters."""
        self._client: Optional[Redis] = None
        self._pubsub: Optional[RedisPubSub] = None
        self._subscriptions = set()
        self._client_params = {
            "host": host or os.environ.get("REDIS_HOST", "localhost"),
            "port": port or int(os.environ.get("REDIS_PORT", 6379)),
            "db": db,
            "password": password,
            "decode_responses": True,
            **kwargs,
        }

    @property
    def client(self) -> Redis:
        """Get the Redis client, initializing it if necessary."""
        if self._client is None:
            self._client = Redis(**self._client_params)
        return self._client

    async def _ensure_connected(self) -> None:
        """Ensure the Redis client is connected."""
        if self._client is None:
            self._client = Redis(**self._client_params)
        if self._pubsub is None:
            self._pubsub = self._client.pubsub()
        try:
            await self._client.ping()
        except RedisConnectionError as e:
            logger.error("Redis connection error: %s", e)
            raise PubSubConnectionError(f"Redis connection error: {e}") from e

    async def publish(self, channel: str, message: Union[str, Dict[str, Any]]) -> None:
        """Publish a message to a channel."""
        try:
            await self._ensure_connected()
            msg = json.dumps(message) if isinstance(message, dict) else str(message)
            await self.client.publish(channel, msg)
            logger.debug("Published message to channel", channel=channel, message=msg)
        except RedisConnectionError as e:
            logger.error("Failed to publish message", channel=channel, error=str(e))
            raise PubSubPublishError(f"Failed to publish message: {e}") from e

    async def subscribe(self, channel: str) -> None:
        """Subscribe to a channel."""
        await self._ensure_connected()

        if channel not in self._subscriptions:
            await self._pubsub.subscribe(channel)
            self._subscriptions.add(channel)
            logger.debug("Subscribed to channel", channel=channel)

    def _decode_message(self, message_data: Union[str, bytes]) -> Dict[str, Any]:
        """Decode message data, attempting JSON deserialization."""
        try:
            decoded_message = (
                message_data.decode()
                if isinstance(message_data, bytes)
                else message_data
            )
            data = json.loads(decoded_message)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, AttributeError):
            pass  # Not a JSON object, or not decodable as string
        return {"data": message_data}

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        if self._pubsub is not None and channel in self._subscriptions:
            await self._pubsub.unsubscribe(channel)
            self._subscriptions.discard(channel)
            logger.debug("Unsubscribed from channel", channel=channel)

    async def close(self) -> None:
        """Close the client and release any resources."""
        if self._pubsub is not None:
            if self._subscriptions:
                await self._pubsub.unsubscribe(*self._subscriptions)
                self._subscriptions.clear()
            await self._pubsub.close()
            self._pubsub = None
        if self._client is not None:
            await self._client.close()
            self._client = None
        logger.debug("Closed Redis Pub/Sub client")
