from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class StreamMessage:
    """Represents a message in an event stream."""
    id: str
    data: Dict[str, Any]
    stream: str
    timestamp: datetime


@dataclass
class PendingMessage(StreamMessage):
    """Represents a pending message in a consumer group."""
    consumer: str
    delivery_time: datetime
    delivery_count: int


class EventStreamClient(ABC):
    """
    An abstract client for a durable, persistent Event Streaming model.

    This is designed for reliable message processing where:
    - Messages are stored persistently and can be replayed
    - Multiple consumer groups can process the same messages
    - Within a consumer group, each message is processed by one consumer
    - Messages can be acknowledged to track processing progress
    - Failed messages can be reprocessed
    """

    @abstractmethod
    async def publish(self, stream: str, data: Dict[str, Any]) -> str:
        """
        Publish an event to a stream.

        Args:
            stream: The name of the stream
            data: The event data to publish

        Returns:
            str: The ID of the published message
        """
        pass

    @abstractmethod
    async def create_consumer_group(
        self,
        stream: str,
        group: str,
        start_id: str = "0"
    ) -> bool:
        """
        Create a new consumer group for a stream.

        Note: The behavior varies by provider:
        - Redis: Requires explicit group creation before use
        - Kafka: Groups are created automatically on first consumer connection
        - RabbitMQ: Uses different consumer group concepts

        Implementations should handle these differences appropriately while
        maintaining consistent behavior from the client perspective.

        Args:
            stream: The name of the stream
            group: The name of the consumer group
            start_id: The ID to start consuming from:
                     "0" - Beginning of stream
                     "$" - Only new messages
                     "id" - Specific message ID

        Returns:
            bool: True if created or if groups are auto-managed,
                 False if the group already exists
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
        last_id: str = ">"
    ) -> List[StreamMessage]:
        """
        Read messages from a consumer group.

        Args:
            stream: The name of the stream
            group: The name of the consumer group
            consumer: The name of the consumer in the group
            count: Maximum number of messages to read
            block: Milliseconds to block waiting for messages
            last_id: ID to start reading from:
                    ">" - Only new messages
                    "0" - All pending messages for this consumer
                    "id" - Start from specific ID

        Returns:
            List of messages with their IDs and data
        """
        pass

    @abstractmethod
    async def acknowledge(
        self,
        stream: str,
        group: str,
        *message_ids: str
    ) -> int:
        """
        Acknowledge that message(s) have been processed.

        Args:
            stream: The name of the stream
            group: The name of the consumer group
            message_ids: One or more message IDs to acknowledge

        Returns:
            int: Number of messages acknowledged
        """
        pass

    @abstractmethod
    async def resume_processing(
        self,
        stream: str,
        group: str,
        consumer: str,
    ) -> List[StreamMessage]:
        """
        Resume processing from where this consumer left off.

        This method ensures exactly-once processing by returning any messages
        that were in process when the consumer disconnected, followed by
        new messages. This implements the "pick up where you left off" pattern,
        which different providers handle in their own way:

        - Redis: Reads pending messages for this consumer, then new messages
        - Kafka: Reads from last committed offset in assigned partitions

        Args:
            stream: The name of the stream
            group: The name of the consumer group
            consumer: The name of this consumer

        Returns:
            List of messages to process, starting from where this
            consumer previously left off
        """
        pass

    @abstractmethod
    async def rebalance_workload(
        self,
        stream: str,
        group: str,
        consumer: str,
        inactive_timeout_ms: int = 30000
    ) -> List[StreamMessage]:
        """
        Claim and process messages from inactive consumers.

        This method implements the load rebalancing pattern, where active
        consumers take over processing from consumers that appear to be
        inactive or failed. Different providers implement this differently:

        - Redis: Claims messages pending > timeout using XCLAIM
        - Kafka: Automatically reassigns partitions in rebalancing

        Args:
            stream: The name of the stream
            group: The name of the consumer group
            consumer: The name of this consumer
            inactive_timeout_ms: How long to wait before considering
                               a consumer inactive (default 30s)

        Returns:
            List of messages claimed from inactive consumers
        """
        pass

    @abstractmethod
    async def stream_info(
        self,
        stream: str
    ) -> Dict[str, Any]:
        """
        Get information about a stream.

        Args:
            stream: The name of the stream

        Returns:
            Dict containing stream metadata (length, groups, etc)
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the event stream client connection."""
        pass
