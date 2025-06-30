"""Factory for creating and configuring Scheduler instances."""
from typing import Any, Dict

import structlog

from ..config import (REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT,
                      get_redis_client)
from ..libs.messaging.event_stream import create_event_stream
from ..libs.messaging.pubsub import create_pubsub_client
from .scheduler import Scheduler

logger = structlog.get_logger(__name__)

async def create_scheduler(config: Dict[str, Any]) -> Scheduler:
    """Create and configure a Scheduler instance with its dependencies.

    Args:
        config: Configuration dictionary.

    Returns:
        A configured Scheduler instance.
    """
    # Initialize Redis client with required parameters
    redis_client = await get_redis_client(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD
    )

    # Create pubsub and event stream with the initialized client
    pubsub = await create_pubsub_client(redis_client=redis_client)
    event_stream = await create_event_stream(redis_client=redis_client)

    return Scheduler(
        id=str(config.get('scheduler_id', '1')),
        redis_client=redis_client,
        pubsub=pubsub,
        event_stream=event_stream,
        config=config,
    )