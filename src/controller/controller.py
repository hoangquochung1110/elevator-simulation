"""
Elevator Controller Service

This service controls an individual elevator, handling its movement,
door operations, and destination management. It interacts with Redis
according to the patterns defined in the architecture document.
"""

import asyncio
import json
import logging

from src.config import ELEVATOR_COMMANDS, ELEVATOR_STATUS, NUM_FLOORS
from src.libs.cache import cache
from src.libs.messaging.pubsub import create_pubsub_service
from src.models.elevator import DoorStatus, Elevator, ElevatorStatus

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class ElevatorController:
    """
    Service that controls an individual elevator.

    This service:
    1. Listens for commands on elevator:commands:{id}
    2. Publishes status updates on elevator:status:{id}
    3. Persists state in Redis
    4. Manages the elevator's destinations
    """

    def __init__(self, elevator_id: int, initial_floor: int = 1):
        """
        Initialize the elevator service.

        Args:
            elevator_id: Unique identifier for this elevator
            initial_floor: The floor where this elevator starts
        """
        self.elevator = Elevator(
            elevator_id=elevator_id, initial_floor=initial_floor
        )
        # Set up subscriber for command channel
        self.command_channel = ELEVATOR_COMMANDS.format(elevator_id)
        self.status_channel = ELEVATOR_STATUS.format(elevator_id)
        self._running = False
        self._movement_task = None
        self.elevator_state = None
        self.pubsub = create_pubsub_service()

    async def start(self) -> None:
        """
        Start the elevator service.

        This starts the command subscriber and initializes the elevator state.
        """
        self._running = True
        # Set up subscriber for command channel
        await self.pubsub.subscribe(self.command_channel)

        # Load initial elevator states
        await self._load_elevator_state()

        try:
            while self._running:
                msg = await self.pubsub.get_message(timeout=1.0)
                if msg is not None:
                    await self._handle_command(msg)
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the elevator service."""
        self._running = False
        # unsubscribe from all channels and patterns, then close pubsub
        await self.pubsub.unsubscribe(self.command_channel)
        await self.pubsub.close()

        if self._movement_task:
            self._movement_task.cancel()
            try:
                await self._movement_task
            except asyncio.CancelledError:
                pass

        logger.info("service_stopped: elevator_id=%s", self.elevator.id)

    async def _handle_command(self, message) -> None:
        """
        Handle an incoming command message from Redis.

        Args:
            message: The Redis pub/sub message
        """
        # Skip subscribe/unsubscribe messages
        print(message)

        try:
            data = message
            command = data.get("command")
            logger.info(
                "received_command: elevator_id=%s, command=%s",
                self.elevator.id,
                command,
            )
            if command == "go_to_floor":
                await self.go_to_floor(data.get("floor"))
            if command == "add_destination":
                await self.add_destination(data.get("floor"))

        except json.JSONDecodeError:
            logger.error(
                "invalid_json: elevator_id=%s, raw_message=%s",
                self.elevator.id,
                message,
                exc_info=True,
            )

    async def go_to_floor(self, floor: int) -> None:
        """
        Command the elevator to go to a specific floor.

        Args:
            floor: The target floor
        """

        if floor < 1 or floor > NUM_FLOORS:
            logger.warning("invalid_floor: floor=%s", floor)
            raise ValueError

        if floor == self.elevator.current_floor:
            logger.info(
                "duplicate_floor_request: floor=%s",
                self.elevator.current_floor,
            )
            # Already at this floor, just open the door
            await self.open_door()
            # Wait for passengers to enter/exit, then close door
            await asyncio.sleep(2)
            await self.close_door()
            return

        # Add as highest priority destination
        await self.add_destination(floor, priority=0)

    async def open_door(self) -> None:
        """Open the elevator door."""
        if self.elevator.door_status == DoorStatus.OPEN:
            return

        # Set status
        self.elevator.door_status = DoorStatus.OPEN

        # Publish status update
        await self._publish_status()
        await self._persist_state()

        # Wait for door operation time
        await asyncio.sleep(self.elevator.door_operation_time)

        logger.info(
            "doors_opened: elevator_id=%s, floor=%s",
            self.elevator.id,
            self.elevator.current_floor,
        )

    async def close_door(self) -> None:
        """Close the elevator door."""
        if self.elevator.door_status == DoorStatus.CLOSED:
            return

        # Set status
        self.elevator.door_status = DoorStatus.CLOSED

        # Publish status update
        await self._publish_status()
        await self._persist_state()

        # Wait for door operation time
        await asyncio.sleep(self.elevator.door_operation_time)

        logger.info(
            "doors_closed: elevator_id=%s, floor=%s",
            self.elevator.id,
            self.elevator.current_floor,
        )

    async def add_destination(self, floor: int, priority: int = 1) -> None:
        """
        Add a destination to the elevator's queue.

        Args:
            floor: The target floor
            priority: Priority (lower number = higher priority)
        """
        if floor < 1 or floor > NUM_FLOORS:
            logger.warning("invalid_floor: floor=%s", floor)
            return

        if floor == self.elevator.current_floor:
            logger.info(
                "duplicate_floor_request: floor=%s",
                self.elevator.current_floor,
            )
            await self.open_door()
            await asyncio.sleep(2)
            await self.close_door()
            return
        # Update elevator model
        self.elevator.add_destination(floor)

        # Publish status update
        await self._publish_status()

        # Start movement if not already moving
        if not self._movement_task or self._movement_task.done():
            self._movement_task = asyncio.create_task(self._process_movement())

    async def _publish_status(self):
        """Publish the current elevator status to Redis."""
        # Format status for publishing
        try:
            # Try to get current loop time, fall back to time.time() if loop closed
            loop_time = asyncio.get_event_loop().time()
        except RuntimeError:
            # Event loop might be closed in test environment
            import time

            loop_time = time.time()

        status = {
            "id": self.elevator.id,
            "current_floor": self.elevator.current_floor,
            "status": self.elevator.status.value,
            "door_status": self.elevator.door_status.value,
            "timestamp": loop_time,
            "destinations": self.elevator.destinations,
        }

        # Publish to status channel
        await self.pubsub.publish(self.status_channel, json.dumps(status))

    async def _persist_state(self):
        await cache.set(
            self.status_channel, json.dumps(self.elevator.to_dict())
        )

    async def _load_elevator_state(self) -> None:
        key = self.status_channel
        state = await cache.get(key)
        if state:
            self.elevator = Elevator.from_dict(state)
        else:
            logger.warning(
                "elevator_state_not_found: elevator_id=%s", self.elevator.id
            )

    async def _process_movement(self) -> None:
        """
        Process elevator movement based on queued destinations.
        Runs as a background task when the elevator has destinations.
        """
        try:
            while self._running and self.elevator.destinations:
                # Get next floor from in-memory queue
                next_floor = self.elevator.destinations.pop(0)
                # Determine movement direction
                if next_floor > self.elevator.current_floor:
                    self.elevator.status = ElevatorStatus.MOVING_UP
                elif next_floor < self.elevator.current_floor:
                    self.elevator.status = ElevatorStatus.MOVING_DOWN
                # Publish status and persist state
                await self._publish_status()
                await self._persist_state()
                # Calculate movement time
                floors = abs(next_floor - self.elevator.current_floor)
                movement_time = floors * self.elevator.floor_travel_time
                logger.info(
                    "moving_to_floor: elevator_id=%s, current_floor=%s, next_floor=%s, movement_time=%s",
                    self.elevator.id,
                    self.elevator.current_floor,
                    next_floor,
                    movement_time,
                )
                await asyncio.sleep(movement_time)
                # Arrive at next floor
                self.elevator.current_floor = next_floor
                self.elevator.status = ElevatorStatus.IDLE
                await self._publish_status()
                await self._persist_state()
                logger.info(
                    "arrived_at_floor: elevator_id=%s, floor=%s",
                    self.elevator.id,
                    self.elevator.current_floor,
                )
                # Open doors and wait
                await self.open_door()
                await asyncio.sleep(2)
                await self.close_door()
        except asyncio.CancelledError:
            logger.info(
                "Elevator %s movement task cancelled", self.elevator.id
            )
            raise
        finally:
            # Reset movement task
            self._movement_task = None
