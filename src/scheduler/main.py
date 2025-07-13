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

import structlog

from src.config import (
    REDIS_DB,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    configure_logging,
)
from src.libs.cache import close as close_cache
from src.libs.cache import init_cache
from src.libs.messaging.event_stream import close as close_event_stream
from src.libs.messaging.event_stream import init_event_stream
from src.libs.messaging.pubsub import close as close_pubsub
from src.libs.messaging.pubsub import init_pubsub
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


async def main():
    """Main entry point for the Scheduler service."""
    # Configuration
    config = {
        "scheduler_id": os.getenv("SCHEDULER_ID", "1"),
        "event_stream_config": {
            "provider": os.getenv("EVENT_STREAM_PROVIDER", "redis"),
        },
    }

    scheduler = None
    try:
        # Initialize services
        init_cache(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD
        )
        init_event_stream(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD
        )
        init_pubsub(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD
        )

        # Log service startup
        logger.info(
            "scheduler_starting",
            scheduler_id=config["scheduler_id"],
        )

        # Create and start scheduler
        scheduler = await create_scheduler(config)
        scheduler_task = asyncio.create_task(scheduler.start())

        # Wait for shutdown signal
        await shutdown_event.wait()

    except Exception as e:
        logger.error("scheduler_error", error=str(e), exc_info=True)
        sys.exit(1)
    finally:
        if scheduler is not None:
            await scheduler.stop()
        await close_cache()
        await close_event_stream()
        await close_pubsub()
        logger.info("Scheduler shutdown complete")


if __name__ == "__main__":
    configure_logging()
    handle_signals()
    asyncio.run(main())
