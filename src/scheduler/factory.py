"""Factory for creating and configuring Scheduler instances."""
from typing import Dict, Any

from ..config import get_redis_client
from ..libs.messaging.event_stream import create_event_stream
from ..libs.messaging.pubsub import create_pubsub_client
from .scheduler import Scheduler


async def create_scheduler(config: Dict[str, Any]) -> Scheduler:
    """Create and configure a Scheduler instance with its dependencies.
    
    Args:
        config: Configuration dictionary containing:
            - scheduler_id: Unique ID for the scheduler
            - redis_config: Configuration for Redis client (not used directly, kept for backward compatibility)
            - pubsub_config: Configuration for PubSub client
            - event_stream_config: Configuration for EventStream client
            
    Returns:
        Configured Scheduler instance
    """
    # Initialize dependencies
    # Note: get_redis_client() reads from environment variables directly
    redis_client = await get_redis_client()
    pubsub = await create_pubsub_client(**config.get('pubsub_config', {}))
    event_stream = await create_event_stream(**config.get('event_stream_config', {}))
    
    # Create and return scheduler
    return Scheduler(
        id=str(config['scheduler_id']),  # Ensure ID is string
        redis_client=redis_client,
        pubsub=pubsub,
        event_stream=event_stream,
        config=config
    )
