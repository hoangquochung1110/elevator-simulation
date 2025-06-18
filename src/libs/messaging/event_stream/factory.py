from enum import Enum
from typing import Any, Dict, Optional

from .base import EventStreamClient
from .redis import create_redis_stream


class StreamProvider(Enum):
    """Supported Event Stream providers."""
    REDIS = "redis"
    # Easy to add more providers:
    # KAFKA = "kafka"
    # NATS = "nats"
    # PULSAR = "pulsar"


async def create_stream_client(
    provider: StreamProvider,
    config: Optional[Dict[str, Any]] = None
) -> EventStreamClient:
    """
    Create an Event Stream client for the specified provider.

    Args:
        provider: The stream provider to use
        config: Provider-specific configuration options

    Example:
        # Redis with default config
        stream = await create_stream_client(StreamProvider.REDIS)

        # Redis with custom config
        stream = await create_stream_client(
            StreamProvider.REDIS,
            {
                "host": "redis.example.com",
                "port": 6380,
                "password": "secret",
                "cluster_mode": True
            }
        )

    Returns:
        An Event Stream client for the specified provider

    Raises:
        ValueError: If the provider is not supported
    """
    config = config or {}

    if provider == StreamProvider.REDIS:
        return await create_redis_stream(**config)

    raise ValueError(f"Unsupported stream provider: {provider}")
