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
from contextlib import asynccontextmanager

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


@asynccontextmanager
async def scheduler_lifecycle():
    """Context manager for scheduler lifecycle management.

    Yields:
        Scheduler: The initialized scheduler instance
    """
    scheduler = None
    try:
        # Log service startup
        logger.info("scheduler_starting")

        # Create and start scheduler
        scheduler = await create_scheduler(id=1)
        asyncio.create_task(scheduler.start())

        yield scheduler

    except Exception as e:
        logger.error("scheduler_error", error=str(e))
        raise
    finally:
        if scheduler:
            await scheduler.stop()
        logger.info("scheduler_stopped")


async def main():
    """Main entry point for the Scheduler service."""
    try:
        async with scheduler_lifecycle() as scheduler:
            # Keep the service running until shutdown signal
            await shutdown_event.wait()
            logger.info("shutdown_signal_received")
    except asyncio.CancelledError:
        logger.info("scheduler_shutdown_requested")
    except Exception as e:
        logger.error("unexpected_error", error=str(e))
        raise


if __name__ == "__main__":
    configure_logging()
    handle_signals()
    asyncio.run(main())
