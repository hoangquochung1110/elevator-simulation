"""Factory for creating and configuring Scheduler instances."""
from typing import Any, Dict

import structlog

from ..config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT
from ..libs.cache import cache
from ..libs.messaging.pubsub import create_pubsub_client
from .scheduler import Scheduler

logger = structlog.get_logger(__name__)


async def create_scheduler(config: Dict[str, Any]) -> Scheduler:
    """Create and configure a Scheduler instance with its dependencies."""
    # The cache and event_stream services are now initialized in the main entry point.
    redis_client = cache._backend.client
    pubsub = await create_pubsub_client(redis_client=redis_client)

    return Scheduler(
        id=str(config.get("scheduler_id", "1")),
        pubsub=pubsub,
        config=config,
    )
