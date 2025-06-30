from abc import ABC, abstractmethod


async def create_event_stream(provider='redis', **kwargs):
    """Factory function to create an event stream client.

    Args:
        provider: The event stream provider to use ('redis' is the default and currently only option)
        **kwargs: Additional arguments to pass to the provider's create function

    Returns:
        An instance of EventStreamClient

    Example:
        # Create a Redis stream client with default settings
        stream = await create_event_stream()

        # Create with custom Redis connection
        stream = await create_event_stream(
            host='redis.example.com',
            port=6380,
            password='secret'
        )
    """
    if provider == 'redis':
        from .redis import create_redis_stream
        return await create_redis_stream(**kwargs)
    else:
        raise ValueError(f"Unsupported event stream provider: {provider}")


class EventStreamClient(ABC):
    """Abstract base class for event stream clients.

    This defines the interface that all event stream implementations must follow.
    """

    @abstractmethod
    async def publish(self, stream, data):
        """Publish an event to a stream.

        Args:
            stream: Name of the stream to publish to
            data: The event data (any serializable type)

        Returns:
            The message ID of the published event
        """
        pass

    @abstractmethod
    async def create_consumer_group(self, stream, group):
        """Create a consumer group for a stream.

        Args:
            stream: Name of the stream
            group: Name of the consumer group to create

        Returns:
            True if the consumer group was created successfully
        """
        pass

    @abstractmethod
    async def read_group(self, stream, group, consumer, count=None, block=None, last_id=">"):
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
    async def acknowledge(self, stream, group, *message_ids):
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
    async def resume_processing(self, stream, group, consumer):
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
    async def rebalance_workload(self, stream, group, consumer, inactive_timeout_ms=30000):
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
    async def get_pending(self, stream, group, consumer=None, count=None):
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
    async def claim_pending(self, stream, group, consumer, min_idle_time, *message_ids):
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
    async def stream_info(self, stream):
        """Get information about a stream.

        Args:
            stream: Name of the stream

        Returns:
            Stream information
        """
        pass

    @abstractmethod
    async def close(self):
        """Close the connection to the event stream."""
        pass