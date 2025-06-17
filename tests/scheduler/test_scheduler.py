import asyncio
import json

import pytest
from redis.exceptions import ConnectionError, RedisError

from src.config import ELEVATOR_STATUS
from src.models.elevator import ElevatorStatus
from src.models.request import Direction, ExternalRequest
from src.scheduler.scheduler import Scheduler, redis_xreadgroup_with_ack


async def test_scheduler_handles_external_request(redis_client, elevators):
    # Arrange
    scheduler = Scheduler(id="test-1")
    scheduler.redis_client = redis_client

    # Set initial elevator state
    initial_state = {
        "id": 1,
        "current_floor": 1,
        "status": "idle",
        "door_status": "closed",
        "destinations": []
    }
    await redis_client.set(
        ELEVATOR_STATUS.format(1),
        json.dumps(initial_state)
    )

    await scheduler._load_elevator_states()

    request = ExternalRequest(
        floor=3,
        direction=Direction.UP
    )

    # Act
    elevator_id = await scheduler._select_best_elevator_for_external(request)

    # Assert
    assert elevator_id is not None
    assert isinstance(elevator_id, int)
    assert elevator_id == 1


async def test_scheduler_handles_connection_retry(redis_client, mocker):
    # Arrange
    scheduler = Scheduler(id="test-1")
    scheduler.redis_client = redis_client

    # Mock Redis xreadgroup to simulate persistent connection errors
    mock_xreadgroup = mocker.patch.object(redis_client, 'xreadgroup')

    # Create a list of futures that raise ConnectionError
    async def raise_error(*args, **kwargs):
        raise ConnectionError("Test connection error")

    mock_xreadgroup.side_effect = raise_error

    # Mock Redis xack for success
    mock_xack = mocker.patch.object(redis_client, 'xack')
    mock_xack.return_value = True

    # Act & Assert - Should retry and eventually fail
    with pytest.raises(ConnectionError):
        async with redis_xreadgroup_with_ack(
            redis_client,
            "test-group",
            "test-consumer",
            {"test-stream": ">"},
            auto_ack=False,
            max_retries=2
        ) as stream_entries:
            pass

    # Verify number of retry attempts
    assert mock_xreadgroup.call_count == 2
    assert not mock_xack.called  # Should not reach ack step due to persistent error


async def test_scheduler_calculates_correct_scores(redis_client):
    # Arrange
    scheduler = Scheduler(id="test-1")
    scheduler.redis_client = redis_client

    # Set up elevator states
    states = {
        1: {
            "id": 1,
            "current_floor": 1,
            "status": "idle",
            "door_status": "closed",
            "destinations": []
        },
        2: {
            "id": 2,
            "current_floor": 5,
            "status": "moving_up",
            "door_status": "closed",
            "destinations": [6]
        },
        3: {  # Added elevator 3 to match NUM_ELEVATORS
            "id": 3,
            "current_floor": 10,
            "status": "idle",
            "door_status": "closed",
            "destinations": []
        }
    }

    for elevator_id, state in states.items():
        await redis_client.set(
            ELEVATOR_STATUS.format(elevator_id),
            json.dumps(state)
        )

    await scheduler._load_elevator_states()

    request = ExternalRequest(
        floor=2,
        direction=Direction.UP
    )

    # Act
    elevator_id = await scheduler._select_best_elevator_for_external(request)

    # Assert - Should select elevator 1 as it's idle and closer
    assert elevator_id == 1