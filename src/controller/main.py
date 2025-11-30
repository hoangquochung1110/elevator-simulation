#!/usr/bin/env python3
"""
Scheduler Service Entry Point

This module runs the elevator scheduler as a standalone service.
It listens to elevator requests and assigns them to the most appropriate elevator.
"""

import asyncio
import signal

import logging

from src.config import NUM_ELEVATORS
from src.controller.controller import ElevatorController

# Configure logging to work with OpenTelemetry auto-instrumentation
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


async def shutdown(sig, loop):
    """Cleanup tasks tied to the service's shutdown."""
    logger.info("Received exit signal %s...", sig.name)

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    for task in tasks:
        task.cancel()

    logger.info("Cancelling %d outstanding tasks", len(tasks))
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def main():
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )

    controllers = []
    try:
        # Dynamically create controllers based on config
        controllers = [
            ElevatorController(elevator_id=i + 1) for i in range(NUM_ELEVATORS)
        ]

        # Start all controllers
        logger.info("Starting elevator controller service...")
        start_tasks = [c.start() for c in controllers]
        await asyncio.gather(*start_tasks)

        # Keep the service running until shutdown signal is received
        logger.info("Elevator controller service started")
        while True:
            await asyncio.sleep(3600)  # Long sleep to reduce CPU usage

    except asyncio.CancelledError:
        logger.info("Shutdown sequence initiated")
    except Exception as e:
        logger.error("Error in controller service: %s", e)
        raise
    finally:
        logger.info("Shutting down controllers...")
        if controllers:
            stop_tasks = [c.stop() for c in controllers]
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        logger.info("All controllers stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by keyboard interrupt")
    except Exception as e:
        logger.error("Service failed: %s", e)
        raise
    finally:
        logger.info("Service shutdown complete")
