from enum import Enum
from typing import Any, Dict, Optional

from .base import PubSubClient
from .redis import create_redis_pubsub


class PubSubProvider(Enum):
    """Supported PubSub providers/engines."""
    REDIS = "redis"
    # Easy to add more providers in the future:
    # KAFKA = "kafka"
    # RABBITMQ = "rabbitmq"
    # NATS = "nats"


async def create_pubsub_client(
    provider: PubSubProvider,
    config: Optional[Dict[str, Any]] = None
) -> PubSubClient:
    """
    Create a PubSub client for the specified provider.

    Args:
        provider: The message broker provider to use
        config: Provider-specific configuration options

    Example:
        # Redis with default config
        pubsub = await create_pubsub_client(PubSubProvider.REDIS)

        # Redis with custom config
        pubsub = await create_pubsub_client(
            PubSubProvider.REDIS,
            {
                "host": "redis.example.com",
                "port": 6380,
                "password": "secret",
                "cluster_mode": True
            }
        )

    Returns:
        A PubSub client instance for the specified provider

    Raises:
        ValueError: If the provider is not supported
    """
    config = config or {}

    if provider == PubSubProvider.REDIS:
        return await create_redis_pubsub(**config)

    raise ValueError(f"Unsupported PubSub provider: {provider}")
