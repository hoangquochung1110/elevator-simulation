"""
Elevator Controller Service

This service controls an individual elevator, handling its movement,
door operations, and destination management. It interacts with Redis
according to the patterns defined in the architecture document.
"""

import asyncio
import json
import logging
from typing import List, Optional

from ..channels import ELEVATOR_COMMANDS, ELEVATOR_STATUS
from ..config import NUM_ELEVATORS, NUM_FLOORS, redis_client
from ..models.elevator import DoorStatus, Elevator, ElevatorStatus
from logging import StreamHandler, Formatter


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
        self.elevator = Elevator(elevator_id=elevator_id, initial_floor=initial_floor)
        self.redis_client = redis_client
        self.pubsub = self.redis_client.pubsub()
        # Set up subscriber for command channel
        self.command_channel = ELEVATOR_COMMANDS.format(elevator_id)
        self.status_channel = ELEVATOR_STATUS.format(elevator_id)
        self._running = False
        self._movement_task = None
        self.elevator_state = None
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = StreamHandler()
        handler.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    async def start(self) -> None:
        """
        Start the elevator service.
        
        This starts the command subscriber and initializes the elevator state.
        """
        self._running = True
        # subscribe to the elevator requests channel
        await self.pubsub.subscribe(self.command_channel)

        # Load initial elevator states
        await self._load_elevator_state()

        async for msg in self.pubsub.listen():
            await self._handle_command(msg)    

    async def stop(self) -> None:
        """Stop the elevator service."""
        self._running = False
        # unsubscribe from all channels and patterns, then close pubsub
        await self.pubsub.unsubscribe()
        await self.pubsub.punsubscribe()
        await self.pubsub.close()
        
        if self._movement_task:
            self._movement_task.cancel()
            try:
                await self._movement_task
            except asyncio.CancelledError:
                pass

        self.logger.info(f"Elevator {self.elevator.id} service stopped")

    async def _handle_command(self, message) -> None:
        """
        Handle an incoming command message from Redis.
        
        Args:
            message: The Redis pub/sub message
        """
        # Skip subscribe/unsubscribe messages
        if message["type"] != "message":
            return

        try:
            data = json.loads(message["data"])
            command = data.get("command")
            if command == "go_to_floor":
                await self.go_to_floor(data.get("floor"))
            if command == "add_destination":
                await self.add_destination(data.get("floor"))

        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in command: {message['data']}")
        except Exception as e:
            self.logger.error(f"Error handling command: {e}")


    async def go_to_floor(self, floor: int):
        """
        Command the elevator to go to a specific floor.
        
        Args:
            floor: The target floor
        """

        if floor < 1 or floor > NUM_FLOORS:
            self.logger.warning(f"Invalid floor requested: {floor}")
            raise ValueError

        if floor == self.elevator.current_floor:
            # Already at this floor, just open the door
            await self.open_door()
            return
            
        # Add as highest priority destination
        await self.add_destination(floor, priority=0)

    async def open_door(self):
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
        
        self.logger.info(f"Elevator {self.elevator.id} doors opened at floor {self.elevator.current_floor}")

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
        
        self.logger.info(f"Elevator {self.elevator.id} doors closed at floor {self.elevator.current_floor}")
    
    async def add_destination(self, floor: int, priority: int = 1) -> None:
        """
        Add a destination to the elevator's queue.
        
        Args:
            floor: The target floor
            priority: Priority (lower number = higher priority)
        """
        if floor < 1 or floor > NUM_FLOORS:
            self.logger.warning(f"Invalid floor requested: {floor}")
            return

        if floor == self.elevator.current_floor:
            return
        # Update elevator model
        self.elevator.add_destination(floor)
        
        # Publish status update
        await self._publish_status()

        # Start movement if not already moving
        if self._movement_task is None or self._movement_task.done():
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
            "destinations": self.elevator.destinations
        }

        # Publish to status channel
        await self.redis_client.publish(self.status_channel, json.dumps(status))

    async def _persist_state(self):
        await self.redis_client.set(self.status_channel, json.dumps(self.elevator.to_dict()))

    async def _load_elevator_state(self) -> None:
        key = ELEVATOR_STATUS.format(self.elevator.id)
        state = await redis_client.get(key)
        if state:
            # Convert to proper types
            self.elevator_state = Elevator.from_dict(json.loads(state))
        else:
            raise ValueError(f"Elevator {elevator_id} not found")

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
                self.logger.info(
                    f"Elevator {self.elevator.id} moving from floor {self.elevator.current_floor} "
                    f"to floor {next_floor}, ETA: {movement_time:.1f}s"
                )
                await asyncio.sleep(movement_time)
                # Arrive at next floor
                self.elevator.current_floor = next_floor
                self.elevator.status = ElevatorStatus.IDLE
                await self._publish_status()
                await self._persist_state()
                self.logger.info(f"Elevator {self.elevator.id} arrived at floor {next_floor}")
                # Open doors and wait
                await self.open_door()
                await asyncio.sleep(2)
                await self.close_door()
        except asyncio.CancelledError:
            self.logger.info(f"Elevator {self.elevator.id} movement task cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in elevator movement: {e}")
        finally:
            # Reset movement task
            self._movement_task = None
