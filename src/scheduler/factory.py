"""Factory for creating and configuring Scheduler instances with dependency injection support."""
from typing import Any, Dict, Optional

import structlog
from redis.asyncio import Redis as RedisClient

from ..config import get_redis_client
from ..libs.messaging.event_stream import (EventStreamClient,
                                           create_event_stream)
from ..libs.messaging.pubsub import PubSubClient, create_pubsub_client
from .scheduler import Scheduler

logger = structlog.get_logger(__name__)

class Dependencies:
    """Container for service dependencies with lazy initialization."""

    def __init__(
        self,
        *,
        redis_client: Optional[RedisClient] = None,
        pubsub: Optional[PubSubClient] = None,
        event_stream: Optional[EventStreamClient] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self._redis_client = redis_client
        self._pubsub = pubsub
        self._event_stream = event_stream
        self.config = config or {}

    async def get_redis(self) -> RedisClient:
        """Get or create Redis client.

        Returns:
            The Redis client instance

        Raises:
            RuntimeError: If Redis client initialization fails
        """
        if self._redis_client is None:
            try:
                self._redis_client = await get_redis_client()
                logger.debug("Successfully initialized Redis client")
            except Exception as e:
                logger.error(
                    "Failed to initialize Redis client",
                    error=str(e),
                    exc_info=True
                )
                raise RuntimeError("Failed to initialize Redis client") from e
        return self._redis_client

    async def get_pubsub(self) -> PubSubClient:
        """Get or create PubSub client."""
        if self._pubsub is None:
            self._pubsub = await create_pubsub_client(
                redis_client=await self.get_redis(),
                **self.config.get('pubsub_config', {})
            )
        return self._pubsub

    async def get_event_stream(self) -> EventStreamClient:
        """Get or create EventStream client."""
        if self._event_stream is None:
            self._event_stream = await create_event_stream(
                redis_client=await self.get_redis(),
                **self.config.get('event_stream_config', {})
            )
        return self._event_stream

# Global instance for production use
_dependencies = Dependencies()

async def create_scheduler(
    config: Dict[str, Any],
    *,
    dependencies: Optional[Dependencies] = None
) -> Scheduler:
    """Create and configure a Scheduler instance with its dependencies.

    Args:
        config: Configuration dictionary containing:
            - scheduler_id: Unique ID for the scheduler
            - pubsub_config: Configuration for PubSub client
            - event_stream_config: Configuration for EventStream client
        dependencies: Optional Dependencies instance for testing

    Returns:
        Configured Scheduler instance
    """
    deps = dependencies or _dependencies
    deps.config = config  # Update config if provided

    return Scheduler(
        id=str(config['scheduler_id']),
        redis_client=await deps.get_redis(),
        pubsub=await deps.get_pubsub(),
        event_stream=await deps.get_event_stream(),
        config=config
    )
