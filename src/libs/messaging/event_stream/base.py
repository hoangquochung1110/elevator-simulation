"""
Abstract base class for event stream clients.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class EventStreamClient(ABC):
    """Abstract base class for event stream clients.

    This defines the interface that all event stream implementations must follow.
    """

    @abstractmethod
    async def publish(self, stream: str, data: Any) -> str:
        """Publish an event to a stream.

        Args:
            stream: Name of the stream to publish to
            data: The event data (any serializable type)

        Returns:
            The message ID of the published event
        """
        pass

    @abstractmethod
    async def create_consumer_group(self, stream: str, group: str) -> bool:
        """Create a consumer group for a stream.

        Args:
            stream: Name of the stream
            group: Name of the consumer group to create

        Returns:
            True if the consumer group was created successfully
        """
        pass

    @abstractmethod
    async def read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: Optional[int] = None,
        block: Optional[int] = None,
        last_id: str = ">",
    ) -> List[Any]:
        """Read messages from a consumer group.

        Args:
            stream: Name of the stream to read from
            group: Name of the consumer group
            consumer: Name of the consumer
            count: Maximum number of messages to return
            block: Block for this many milliseconds if no messages are available
            last_id: ID of the last message read, '>' for new messages

        Returns:
            List of messages
        """
        pass

    @abstractmethod
    async def acknowledge(
        self, stream: str, group: str, *message_ids: str
    ) -> int:
        """Acknowledge messages in a stream.

        Args:
            stream: Name of the stream
            group: Name of the consumer group
            *message_ids: IDs of the messages to acknowledge

        Returns:
            Number of messages acknowledged
        """
        pass

    @abstractmethod
    async def resume_processing(
        self, stream: str, group: str, consumer: str
    ) -> List[Any]:
        """Resume processing from where this consumer left off.

        This should read both pending and new messages.

        Args:
            stream: Name of the stream
            group: Name of the consumer group
            consumer: Name of the consumer

        Returns:
            List of pending and new messages
        """
        pass

    @abstractmethod
    async def rebalance_workload(
        self,
        stream: str,
        group: str,
        consumer: str,
        inactive_timeout_ms: int = 30000,
    ) -> List[Any]:
        """Claim and process messages from inactive consumers.

        Args:
            stream: Name of the stream
            group: Name of the consumer group
            consumer: Name of the consumer claiming the messages
            inactive_timeout_ms: Time in milliseconds after which a consumer is considered inactive

        Returns:
            List of claimed messages
        """
        pass

    @abstractmethod
    async def get_pending(
        self,
        stream: str,
        group: str,
        consumer: Optional[str] = None,
        count: Optional[int] = None,
    ) -> List[Any]:
        """Get pending messages from a consumer group.

        Args:
            stream: Name of the stream
            group: Name of the consumer group
            consumer: Optional consumer name to filter by
            count: Maximum number of messages to return

        Returns:
            List of pending messages
        """
        pass

    @abstractmethod
    async def claim_pending(
        self,
        stream: str,
        group: str,
        consumer: str,
        min_idle_time: int,
        *message_ids: str,
    ) -> List[Any]:
        """Claim pending messages in a stream.

        Args:
            stream: Name of the stream
            group: Name of the consumer group
            consumer: Name of the consumer claiming the messages
            min_idle_time: Minimum idle time in milliseconds
            *message_ids: IDs of the messages to claim

        Returns:
            List of claimed messages
        """
        pass

    @abstractmethod
    async def stream_info(self, stream: str) -> Any:
        """Get information about a stream.

        Args:
            stream: Name of the stream

        Returns:
            Stream information
        """
        pass

    @abstractmethod
    async def range(
        self, stream: str, start: str = "-", end: str = "+"
    ) -> List[Any]:
        """Retrieve entries from a stream within a given range.

        Args:
            stream: Name of the stream
            start: Start ID of the range
            end: End ID of the range

        Returns:
            List of entries
        """
        pass

    @abstractmethod
    async def trim(
        self,
        stream: str,
        min_id: Optional[str] = None,
        maxlen: Optional[int] = None,
        approximate: bool = True,
    ) -> int:
        """Trim a stream to a certain size.

        Args:
            stream: Name of the stream
            min_id: Exclusive start ID; entries with ID < min_id will be removed
            maxlen: Maximum number of entries to keep
            approximate: Whether to use approximate trimming

        Returns:
            Number of trimmed entries
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the connection to the event stream."""
        pass
