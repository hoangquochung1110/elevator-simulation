import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.config import ELEVATOR_STATUS
from src.controller.controller import ElevatorController
from src.models.elevator import DoorStatus, Elevator, ElevatorStatus


async def test_controller_error_handling(redis_client):
    """Test controller handles errors gracefully."""
    controller = None
    try:
        # Arrange
        controller = ElevatorController(elevator_id=1)
        controller.redis_client = redis_client
        controller._running = True

        # Invalid command
        command = {
            "type": "message",
            "data": json.dumps({
                "command": "invalid_command",
                "floor": 5
            })
        }

        # Act & Assert - Should not raise exception
        await controller._handle_command(command)
        # Test passes if no exception is raised
        assert True

    except Exception as e:
        pytest.fail(f"Controller should handle invalid commands gracefully, but raised: {e}")
    finally:
        if controller:
            try:
                controller._running = False
            except Exception:
                pass
