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

from src.config import NUM_ELEVATORS, configure_logging
from src.controller.controller import \
    ElevatorController  # Assuming you move scheduler.py to this location

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

    # dynamically create controllers based on config
    controllers = [ElevatorController(elevator_id=i+1) for i in range(NUM_ELEVATORS)]
    # start scheduler and all controllers
    await asyncio.gather(
        *[c.start() for c in controllers],
    )

if __name__ == "__main__":
    configure_logging()
    handle_signals()
    asyncio.run(main())