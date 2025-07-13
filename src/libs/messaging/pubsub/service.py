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

    # async def listen(self) -> AsyncIterator[Dict[str, Any]]:
    #     return await self._backend.listen()

    async def close(self) -> None:
        if self._backend:
            await self._backend.close()


# Global pub/sub instance
_pubsub_service: Optional[PubSubService] = None


def get_pubsub() -> PubSubService:
    """Get the global pub/sub service instance."""
    global _pubsub_service
    if _pubsub_service is None:
        _pubsub_service = PubSubService()
    return _pubsub_service


def get_local_pubsub(backend=None, **backend_options) -> PubSubService:
    """Create a new, independent pub/sub service instance."""
    return PubSubService(backend, **backend_options)


def init_pubsub(backend=None, **backend_options) -> PubSubService:
    """Initialize the global pub/sub service."""
    global _pubsub_service
    _pubsub_service = PubSubService(backend, **backend_options)
    return _pubsub_service


async def close() -> None:
    """Close the connection to the pub/sub backend."""
    if _pubsub_service:
        await _pubsub_service.close()
