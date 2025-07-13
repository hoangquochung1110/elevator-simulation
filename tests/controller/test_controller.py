import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from src.controller.controller import ElevatorController
from src.models.elevator import DoorStatus, ElevatorStatus


async def test_controller_error_handling(mock_controller_pubsub):
    controller = None
    try:
        # Arrange
        controller = ElevatorController(elevator_id=1)
        controller._running = True

        # Invalid command
        command = {
            "type": "message",
            "data": json.dumps({"command": "invalid_command", "floor": 5}),
        }

        # Act & Assert - Should not raise exception
        await controller._handle_command(command)
        # Test passes if no exception is raised
        assert True

    except Exception as e:
        pytest.fail(
            f"Controller should handle invalid commands gracefully, but raised: {e}"
        )
    finally:
        if controller:
            try:
                controller._running = False
            except Exception:
                pass


async def test_controller_initialization(mock_controller_pubsub):
    """Test ElevatorController initializes correctly."""
    controller = ElevatorController(elevator_id=1)
    assert controller.elevator.id == 1
    assert controller.elevator.current_floor == 1
    assert controller.elevator.status == ElevatorStatus.IDLE
    assert controller.elevator.door_status == DoorStatus.CLOSED
    assert controller.command_channel == "elevator:commands:1"
    assert controller.status_channel == "elevator:status:1"



