"""Abstract base class for pub/sub clients."""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Union


class PubSubClient(ABC):
    """Abstract base class for pub/sub clients.

    This defines the interface that all pub/sub implementations must follow.
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
        """Close the connection to the pub/sub backend."""
        pass