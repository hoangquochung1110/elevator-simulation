#!/usr/bin/env python3
"""
Scheduler Service Entry Point

This module runs the elevator scheduler as a standalone service.
It listens to elevator requests and assigns them to the most appropriate elevator.
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager

from src.scheduler.factory import create_scheduler

# Set up graceful shutdown
shutdown_event = asyncio.Event()

# Configure logging to work with OpenTelemetry auto-instrumentation
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


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
        logger.error("scheduler_error %s", str(e))
        raise
    finally:
        if scheduler:
            await scheduler.stop()
        logger.info("scheduler_stopped")


async def main():
    """Main entry point for the Scheduler service."""
    try:
        async with scheduler_lifecycle():
            # Keep the service running until shutdown signal
            await shutdown_event.wait()
            logger.info("shutdown_signal_received")
    except asyncio.CancelledError:
        logger.info("scheduler_shutdown_requested")
    except Exception as e:
        logger.error("unexpected_error %s", str(e))
        raise


if __name__ == "__main__":
    handle_signals()
    asyncio.run(main())
