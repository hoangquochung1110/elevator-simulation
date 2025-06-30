"""
Pub/Sub messaging client interface and implementations.

This module provides an abstract base class for pub/sub messaging clients
and concrete implementations for different messaging backends.
"""
from __future__ import annotations

import typing
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional, Type, Union


async def create_pubsub_client(provider='redis', **kwargs):
    if provider == 'redis':
        from .redis import create_redis_pubsub
        return await create_redis_pubsub(**kwargs)
    else:
        raise ValueError(f"Unsupported event stream provider: {provider}")

class PubSubClient(ABC):
    """Abstract base class for pub/sub messaging clients.

    This class defines the interface that all concrete pub/sub client
    implementations must follow.
    """

    @abstractmethod
    async def publish(self, channel: str, message: Union[str, Dict[str, Any]]) -> None:
        """Publish a message to a channel.

        Args:
            channel: The channel to publish to.
            message: The message to publish. Can be a string or a dictionary.
        """
        pass

    @abstractmethod
    async def subscribe(self, channel: str) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to a channel and yield messages as they arrive.

        Args:
            channel: The channel to subscribe to.

        Yields:
            Messages received on the channel as dictionaries.
        """
        pass

    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel.

        Args:
            channel: The channel to unsubscribe from.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client and release any resources."""
        pass

    async def __aenter__(self):
        """Support async context manager protocol."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure resources are cleaned up when exiting context."""
        await self.close()
