"""
Elevator model for the simulator.
"""

import time
import enum
import json
from typing import List, Optional


class ElevatorStatus(str, enum.Enum):
    """Possible states of an elevator."""

    IDLE = "idle"
    MOVING_UP = "moving_up"
    MOVING_DOWN = "moving_down"


class DoorStatus(str, enum.Enum):
    """Possible states of elevator doors."""

    OPEN = "open"
    CLOSED = "closed"


class Elevator:
    """
    Represents an elevator in the building.

    Attributes:
        id: Unique identifier of the elevator
        current_floor: The floor where the elevator currently is
        status: Current movement status (idle, moving up, moving down)
        door_status: Whether the door is open or closed
        destinations: Queue of floors this elevator needs to visit
        floor_travel_time: Seconds it takes to travel between consecutive floors
        door_operation_time: Seconds it takes to open or close doors
    """

    def __init__(
        self,
        elevator_id: int,
        initial_floor: int = 1,
        floor_travel_time: float = 1.0,
        door_operation_time: float = 1.5,
    ):
        self.id = elevator_id
        self.current_floor = initial_floor
        self.status = ElevatorStatus.IDLE
        self.door_status = DoorStatus.CLOSED
        self.destinations: List[int] = []
        self.floor_travel_time = floor_travel_time
        self.door_operation_time = door_operation_time

    def add_destination(self, floor: int) -> None:
        """
        Add a floor to visit.

        Args:
            floor: The target floor to add to destinations
        """
        if floor != self.current_floor and floor not in self.destinations:
            self.destinations.append(floor)

    def move_to_next_destination(self) -> Optional[int]:
        """
        Begin moving to the next destination in the queue.

        Returns:
            The target floor or None if no destinations
        """
        if not self.destinations:
            self.status = ElevatorStatus.IDLE
            return None

        next_floor = self.destinations[0]

        if next_floor > self.current_floor:
            self.status = ElevatorStatus.MOVING_UP
        elif next_floor < self.current_floor:
            self.status = ElevatorStatus.MOVING_DOWN

        return next_floor

    def arrive_at_floor(self, floor: int) -> None:
        """
        Process arrival at the specified floor.

        Args:
            floor: The floor we just arrived at
        """
        self.current_floor = floor

        # Remove this floor from destinations if it was our target
        if self.destinations and self.destinations[0] == floor:
            self.destinations.pop(0)

        # If no more destinations, go idle
        if not self.destinations:
            self.status = ElevatorStatus.IDLE

    def open_door(self) -> None:
        """Simulate opening the elevator door."""
        if self.door_status == DoorStatus.CLOSED:
            # Simulate door opening time
            time.sleep(self.door_operation_time)
            self.door_status = DoorStatus.OPEN

    def close_door(self) -> None:
        """Simulate closing the elevator door."""
        if self.door_status == DoorStatus.OPEN:
            # Simulate door closing time
            time.sleep(self.door_operation_time)
            self.door_status = DoorStatus.CLOSED

    def to_dict(self) -> dict:
        """
        Convert elevator state to a dictionary.

        Returns:
            Dictionary representation of elevator state
        """
        return {
            "id": self.id,
            "current_floor": self.current_floor,
            "status": self.status.value,
            "door_status": self.door_status.value,
            "destinations": self.destinations,
        }

    def to_json(self) -> str:
        """
        Convert elevator state to JSON.

        Returns:
            JSON representation of elevator state
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "Elevator":
        """
        Create an Elevator instance from a dictionary.

        Args:
            data: Dictionary containing elevator state

        Returns:
            New Elevator instance
        """
        elevator = cls(
            elevator_id=data["id"], initial_floor=data["current_floor"]
        )
        elevator.status = ElevatorStatus(data["status"])
        elevator.door_status = DoorStatus(data["door_status"])
        elevator.destinations = data.get("destinations", [])
        return elevator

    @classmethod
    def from_json(cls, json_str: str) -> "Elevator":
        """
        Create an Elevator instance from JSON.

        Args:
            json_str: JSON string containing elevator state

        Returns:
            New Elevator instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
