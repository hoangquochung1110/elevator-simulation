"""
Event Stream package for Redis-based event streaming.

This package provides a high-level interface for event streaming operations,
similar to the design of the cache service.

Basic usage:
    >>> from src.libs.messaging.event_stream import event_stream
    >>>
    >>> # Publish an event
    >>> await event_stream.publish('my_stream', {'key': 'value'})
"""

from .service import EventStreamService, get_event_stream, init_event_stream, close
from .exceptions import (
    EventStreamError,
    EventStreamConnectionError,
)

# The global event_stream instance
event_stream = get_event_stream()

__all__ = [
    # Main instance
    'event_stream',

    # Service and initialization
    'EventStreamService',
    'get_event_stream',
    'init_event_stream',
    'close',

    # Exceptions
    'EventStreamError',
    'EventStreamConnectionError',
]