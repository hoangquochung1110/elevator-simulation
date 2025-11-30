"""Redis Pub/Sub client implementation."""

import json
import logging
import os
import asyncio
import importlib
from typing import Any, Dict, Optional, Union, AsyncIterator

# Use relative imports within the package to satisfy type checker/package resolution
from ..base import PubSubClient
from ..exceptions import PubSubConnectionError, PubSubPublishError

# Dynamically import redis asyncio modules to avoid hard dependency during type checking
try:
    _redis_asyncio = importlib.import_module("redis.asyncio")
except Exception:
    _redis_asyncio = None


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
        self._client: Optional[Any] = None
        self._pubsub: Optional[Any] = None
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
    def client(self) -> Any:
        """Get the Redis client, initializing it if necessary."""
        if self._client is None:
            if _redis_asyncio is None:
                raise PubSubConnectionError(
                    "redis.asyncio module is not available"
                )
            self._client = _redis_asyncio.Redis(**self._client_params)
        return self._client

    async def _ensure_connected(self) -> None:
        """Ensure the Redis client is connected."""
        if self._client is None:
            if _redis_asyncio is None:
                raise PubSubConnectionError(
                    "redis.asyncio module is not available"
                )
            self._client = _redis_asyncio.Redis(**self._client_params)
        assert self._client is not None
        if self._pubsub is None:
            self._pubsub = self._client.pubsub()
        try:
            await self._client.ping()
        except Exception as e:
            logger.error("Redis connection error: %s", e)
            raise PubSubConnectionError(f"Redis connection error: {e}") from e

    async def publish(
        self, channel: str, message: Union[str, Dict[str, Any]]
    ) -> None:
        """Publish a message to a channel."""
        try:
            await self._ensure_connected()
            msg = (
                json.dumps(message)
                if isinstance(message, dict)
                else str(message)
            )
            await self.client.publish(channel, msg)
            logger.debug("Published message to channel %s: %s", channel, msg)
        except Exception as e:
            logger.error(
                "Failed to publish message to channel %s: %s", channel, str(e)
            )
            raise PubSubPublishError(f"Failed to publish message: {e}") from e

    async def subscribe(self, channel: str) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to a channel and return an async iterator of messages."""
        await self._ensure_connected()

        pubsub = self._pubsub
        assert pubsub is not None

        if channel not in self._subscriptions:
            await pubsub.subscribe(channel)
            self._subscriptions.add(channel)
            logger.debug("Subscribed to channel %s", channel)

        async def _message_iterator() -> AsyncIterator[Dict[str, Any]]:
            while True:
                msg = await self.get_message(timeout=1.0)
                if msg is not None:
                    yield msg
                else:
                    # Avoid tight loop when no messages
                    await asyncio.sleep(0.05)

        return _message_iterator()

    def _decode_message(
        self, message_data: Union[str, bytes]
    ) -> Dict[str, Any]:
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
            logger.debug("Unsubscribed from channel %s", channel)

    async def get_message(
        self, timeout: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """Get the next message from subscribed channels.

        Args:
            timeout: Maximum time in seconds to wait for a message.

        Returns:
            The message dictionary if available, None if no message was received
            within the timeout.
        """
        if not self._subscriptions or self._pubsub is None:
            return None

        message = await self._pubsub.get_message(timeout=timeout)
        if message and message["type"] == "message":
            return self._decode_message(message["data"])
        return None

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
