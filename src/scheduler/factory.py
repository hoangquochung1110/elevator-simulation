"""Factory for creating and configuring Scheduler instances."""
import structlog

from .scheduler import Scheduler

logger = structlog.get_logger(__name__)


async def create_scheduler(id) -> Scheduler:
    """Create and configure a Scheduler instance with its dependencies."""
    # The cache and event_stream services are now initialized in the main entry point.
    # The pubsub service is now initialized in the main entry point.
    # We can directly use the global pubsub instance.


    return Scheduler(id=id)
