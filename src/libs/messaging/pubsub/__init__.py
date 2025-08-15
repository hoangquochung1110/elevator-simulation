"""
Pub/Sub package for Redis-based messaging.

This package provides a high-level interface for pub/sub operations,
similar to the design of the cache service.

Basic usage:
    >>> from src.libs.messaging.pubsub import pubsub
    >>>
    >>> # Publish a message
    >>> await pubsub.publish('my_channel', {'key': 'value'})
"""

from .exceptions import (
    PubSubClosedError,
    PubSubConnectionError,
    PubSubError,
    PubSubPublishError,
    PubSubSubscribeError,
    PubSubTimeoutError,
    PubSubUnsubscribeError,
)
from .service import PubSubService, close, create_pubsub_service, get_pubsub

# The global pubsub instance
pubsub = get_pubsub()

__all__ = [
    # Main instance
    "pubsub",
    # Service and initialization
    "PubSubService",
    "get_pubsub",
    "create_pubsub_service",
    "close",
    # Exceptions
    "PubSubError",
    "PubSubConnectionError",
    "PubSubPublishError",
    "PubSubSubscribeError",
    "PubSubUnsubscribeError",
    "PubSubTimeoutError",
    "PubSubClosedError",
]
