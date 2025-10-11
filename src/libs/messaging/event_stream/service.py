"""
Event Stream service implementation.

This module provides a high-level interface for event streaming operations,
with Redis as the default backend.
"""
import logging
from typing import Any, List, Optional, Union

from .base import EventStreamClient
from .redis import RedisStreamClient

logger = logging.getLogger(__name__)


class EventStreamService:
    """High-level event stream service with a simple interface."""

    _instance: Optional["EventStreamService"] = None
    _backend: Optional[EventStreamClient] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern."""
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self, backend: Optional[Union[str, EventStreamClient]] = None, **backend_options
    ) -> None:
        """Initialize the event stream service."""
        if self._initialized:
            return

        if backend is None or backend == "redis":
            self._backend = RedisStreamClient(**backend_options)
        elif isinstance(backend, EventStreamClient):
            self._backend = backend
        else:
            raise ValueError(f"Unsupported event stream backend: {backend}")

        self._initialized = True

    async def publish(self, stream: str, data: Any) -> str:
        backend = self._backend
        assert backend is not None
        return await backend.publish(stream, data)

    async def create_consumer_group(self, stream: str, group: str) -> bool:
        """Create a consumer group on the event stream backend."""
        backend = self._backend
        assert backend is not None
        return await backend.create_consumer_group(stream, group)

    async def read_group(self, **kwargs):
        backend = self._backend
        assert backend is not None
        return await backend.read_group(**kwargs)

    async def acknowledge(self, stream: str, group: str, *message_ids: str):
        backend = self._backend
        assert backend is not None
        return await backend.acknowledge(stream, group, *message_ids)

    async def range(self, stream: str, start: str = "-", end: str = "+") -> List[Any]:
        backend = self._backend
        assert backend is not None
        return await backend.range(stream, start, end)

    async def trim(
        self,
        stream: str,
        min_id: Optional[str] = None,
        maxlen: Optional[int] = None,
        approximate: bool = True,
    ) -> int:
        backend = self._backend
        assert backend is not None
        return await backend.trim(stream, min_id, maxlen, approximate)

    async def close(self) -> None:
        backend = self._backend
        if backend is not None:
            await backend.close()


# Global event stream instance
_event_stream_service = None


def get_event_stream() -> EventStreamService:
    """Get the global event stream service instance."""
    global _event_stream_service
    if _event_stream_service is None:
        _event_stream_service = EventStreamService()
    return _event_stream_service


def init_event_stream(backend=None, **backend_options) -> EventStreamService:
    """Initialize the global event stream service."""
    global _event_stream_service
    _event_stream_service = EventStreamService(backend, **backend_options)
    return _event_stream_service


async def close() -> None:
    """Close the connection to the event stream backend."""
    await get_event_stream().close()