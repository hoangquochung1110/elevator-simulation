"""
Convenience module for creating and using pub/sub clients.

This module provides a simple interface for creating and using pub/sub clients
throughout the application.
"""
import os
from typing import Any, Dict, Optional

from .base import create_pubsub_client

# Default configuration
DEFAULT_CONFIG = {
    "host": os.getenv("REDIS_HOST", "redis"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "password": os.getenv("REDIS_PASSWORD"),
    "cluster_mode": os.getenv("REDIS_CLUSTER_MODE", "false").lower() == "true",
}

# Module-level client instance
_client = None


def get_client(config: Optional[Dict[str, Any]] = None) -> 'PubSubClient':
    """Get or create a pub/sub client with the given configuration.

    If a client has already been created, it will be returned regardless of
    the provided configuration.

    Args:
        config: Optional configuration overrides. If not provided, environment
            variables and defaults will be used.

    Returns:
        A pub/sub client instance.
    """
    global _client

    if _client is None:
        # Use provided config or fall back to defaults
        final_config = DEFAULT_CONFIG.copy()
        if config:
            final_config.update(config)

        _client = create_pubsub_client("redis", **final_config)

    return _client


def set_client(client: 'PubSubClient') -> None:
    """Set the module-level pub/sub client.

    This is primarily useful for testing or when you need to use a custom
    client instance.

    Args:
        client: The pub/sub client to use.
    """
    global _client
    _client = client


async def close_client() -> None:
    """Close the module-level pub/sub client if it exists."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
