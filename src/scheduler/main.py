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

from src.config import configure_logging
from src.scheduler.scheduler import \
    Scheduler  # Assuming you move scheduler.py to this location

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
    """
    Main entry point for the Scheduler service.
    """
    # Configure logging for containerized environment

    try:
        # Log service startup
        logger.info("scheduler_starting",
                   redis_host=os.getenv("REDIS_HOST", "localhost"),
                   redis_port=os.getenv("REDIS_PORT", 6379))
        logger.info("Hello world")
        # Initialize scheduler with unique ID (configurable via env var)
        scheduler_id = int(os.getenv("SCHEDULER_ID", 1))
        scheduler = Scheduler(id=scheduler_id)

        # Start scheduler and wait for shutdown signal
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