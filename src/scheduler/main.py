#!/usr/bin/env python3
"""
Scheduler Service Entry Point

This module runs the elevator scheduler as a standalone service.
It listens to elevator requests and assigns them to the most appropriate elevator.
"""

import asyncio
import os
import signal
import sys
from typing import Any, Dict

import structlog

from src.config import configure_logging
from src.scheduler.factory import create_scheduler

# Set up graceful shutdown
shutdown_event = asyncio.Event()

logger = structlog.get_logger(__name__)


def handle_signals():
    """Set up signal handlers for graceful shutdown."""

    def handle_exit(sig, frame):
        print(f"Received exit signal {sig}. Shutting down gracefully...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)


def get_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    # Set Redis environment variables if not already set
    os.environ.setdefault('REDIS_HOST', 'localhost')
    os.environ.setdefault('REDIS_PORT', '6379')
    os.environ.setdefault('REDIS_DB', '0')

    return {
        'scheduler_id': os.getenv('SCHEDULER_ID', '1'),
        # Redis config is read from environment variables directly by get_redis_client()
        'redis_config': {},
        'pubsub_config': {
            'provider': os.getenv('PUBSUB_PROVIDER', 'redis'),
        },
        'event_stream_config': {
            # Add any event stream specific config here
        }
    }


async def main():
    """Main entry point for the Scheduler service."""
    try:
        # Load configuration
        config = get_config()

        # Log service startup
        logger.info(
            "scheduler_starting",
            scheduler_id=config['scheduler_id'],
            **config['redis_config']
        )

        # Create and start scheduler
        scheduler = await create_scheduler(config)
        scheduler_task = asyncio.create_task(scheduler.start())

        # Wait for shutdown signal
        await shutdown_event.wait()

        # Clean up
        logger.info("scheduler_stopping")
        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        logger.info("scheduler_stopped")

    except Exception as e:
        logger.error("scheduler_error", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    configure_logging()
    handle_signals()
    asyncio.run(main())