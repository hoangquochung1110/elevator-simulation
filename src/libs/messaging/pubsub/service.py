"""Pub/Sub service implementation."""

import logging
from typing import Any, AsyncIterator, Dict, Optional, Union

from .backends.redis import RedisPubSubBackend
from .base import PubSubClient

logger = logging.getLogger(__name__)


class PubSubService:
    """High-level pub/sub service with a simple interface."""

    _backend: PubSubClient

    def __init__(
        self,
        backend: Optional[Union[str, PubSubClient]] = None,
        **backend_options,
    ) -> None:
        """Initialize the pub/sub service."""
        if backend is None or backend == "redis":
            self._backend = RedisPubSubBackend(**backend_options)
        elif isinstance(backend, PubSubClient):
            self._backend = backend
        else:
            raise ValueError(f"Unsupported pub/sub backend: {backend}")

    async def publish(self, channel: str, message: Union[str, Dict[str, Any]]) -> None:
        return await self._backend.publish(channel, message)

    async def subscribe(self, channel: str) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to a channel and return an async iterator for messages."""
        return await self._backend.subscribe(channel)

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        await self._backend.unsubscribe(channel)

    async def get_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Get the next message from the subscribed channels.

        Args:
            timeout: Maximum time in seconds to wait for a message

        Returns:
            The message if available, None if no message was received within the timeout
        """
        return await self._backend.get_message(timeout=timeout)

    # async def listen(self) -> AsyncIterator[Dict[str, Any]]:
    #     return await self._backend.listen()

    async def close(self) -> None:
        if self._backend:
            await self._backend.close()


# Global pub/sub instance
_pubsub_service: Optional[PubSubService] = None


def get_pubsub() -> PubSubService:
    """Get the global pub/sub service instance.

    This returns a singleton instance that's shared across the application.
    Use this when you want to share the same pub/sub connection throughout your app.
    """
    global _pubsub_service
    if _pubsub_service is None:
        _pubsub_service = PubSubService()
    return _pubsub_service


def create_pubsub_service(backend=None, **backend_options) -> PubSubService:
    """Create a new, independent pub/sub service instance.

    Use this when you need a dedicated pub/sub connection separate from the global instance.
    This is particularly useful for:
    - Isolating pub/sub connections for different components
    - Creating temporary connections for specific tasks
    - Managing connections with different configurations
    """
    return PubSubService(backend, **backend_options)


async def close() -> None:
    """Close the connection to the global pub/sub backend."""
    if _pubsub_service:
        await _pubsub_service.close()
