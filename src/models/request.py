"""
Request models for the elevator simulator.

This module contains two types of requests:
1. ExternalRequest - Call requests from outside the elevator (floor call buttons)
2. InternalRequest - Destination requests from inside the elevator (floor buttons)
"""

import enum
import time
import uuid
import json
from typing import Optional


class RequestStatus(str, enum.Enum):
    """Possible states of an elevator request."""

    PENDING = "pending"
    COMPLETED = "completed"


class Direction(str, enum.Enum):
    """Direction for external elevator requests."""

    UP = "up"
    DOWN = "down"


class BaseRequest:
    """
    Base class for elevator requests.

    Attributes:
        id: Unique identifier for the request
        timestamp: When the request was created
        status: Current status of the request (pending/completed)
    """

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.timestamp = time.time()
        self.status = RequestStatus.PENDING

    def complete(self) -> None:
        """Mark the request as completed."""
        self.status = RequestStatus.COMPLETED

    def to_dict(self) -> dict:
        """
        Convert request to a dictionary.

        Returns:
            Dictionary representation
        """
        return {"id": self.id, "timestamp": self.timestamp, "status": self.status.value}

    def to_json(self) -> str:
        """
        Convert request to JSON.

        Returns:
            JSON representation
        """
        return json.dumps(self.to_dict())


class ExternalRequest(BaseRequest):
    """
    Request from outside the elevator (floor call button).

    Attributes:
        floor: The floor where the button was pressed
        direction: UP or DOWN direction
    """

    def __init__(self, floor: int, direction: Direction):
        super().__init__()
        self.floor = floor
        self.direction = direction

    def to_dict(self) -> dict:
        """
        Convert external request to a dictionary.

        Returns:
            Dictionary representation
        """
        data = super().to_dict()
        data.update(
            {"type": "external", "floor": self.floor, "direction": self.direction.value}
        )
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ExternalRequest":
        """
        Create an ExternalRequest from a dictionary.

        Args:
            data: Dictionary containing request data

        Returns:
            New ExternalRequest instance
        """
        request = cls(floor=data["floor"], direction=Direction(data["direction"]))
        request.id = data["id"]
        request.timestamp = data["timestamp"]
        request.status = RequestStatus(data["status"])
        return request

    @classmethod
    def from_json(cls, json_str: str) -> "ExternalRequest":
        """
        Create an ExternalRequest from JSON.

        Args:
            json_str: JSON string containing request data

        Returns:
            New ExternalRequest instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


class InternalRequest(BaseRequest):
    """
    Request from inside the elevator (destination button).

    Attributes:
        elevator_id: ID of the elevator where the button was pressed
        destination_floor: The target floor
    """

    def __init__(self, elevator_id: int, destination_floor: int):
        super().__init__()
        self.elevator_id = elevator_id
        self.destination_floor = destination_floor

    def to_dict(self) -> dict:
        """
        Convert internal request to a dictionary.

        Returns:
            Dictionary representation
        """
        data = super().to_dict()
        data.update(
            {
                "type": "internal",
                "elevator_id": self.elevator_id,
                "destination_floor": self.destination_floor,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "InternalRequest":
        """
        Create an InternalRequest from a dictionary.

        Args:
            data: Dictionary containing request data

        Returns:
            New InternalRequest instance
        """
        request = cls(
            elevator_id=data["elevator_id"], destination_floor=data["destination_floor"]
        )
        request.id = data["id"]
        request.timestamp = data["timestamp"]
        request.status = RequestStatus(data["status"])
        return request

    @classmethod
    def from_json(cls, json_str: str) -> "InternalRequest":
        """
        Create an InternalRequest from JSON.

        Args:
            json_str: JSON string containing request data

        Returns:
            New InternalRequest instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
