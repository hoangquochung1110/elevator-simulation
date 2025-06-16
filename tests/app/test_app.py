import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.app.main import app
from src.config import ELEVATOR_REQUESTS_STREAM, ELEVATOR_STATUS, get_redis_client, NUM_ELEVATORS
from src.models.elevator import ElevatorStatus
from src.models.request import Direction


async def test_index_route(async_client):
    """Test the index route synchronously."""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_create_internal_request(async_client, redis_client):
    """Test internal request creation asynchronously."""
    # Mock the Redis operations your app needs
    redis_client.xadd = AsyncMock(return_value=b"test-id")

    # Arrange
    request_data = {
        "elevator_id": 1,
        "destination_floor": 5
    }

    # Patch the get_redis_client dependency in your app
    with patch('src.config.get_redis_client', return_value=redis_client):
        response = await async_client.post("/api/requests/internal", json=request_data)

    # Assert
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["channel"] == ELEVATOR_REQUESTS_STREAM


@pytest.mark.asyncio
async def test_get_elevator_states(async_client, redis_client):
    """Test elevator states retrieval asynchronously."""
    # Arrange - Set up all required elevators for test
    elevator_states = [
        {
            "id": i,
            "current_floor": 1,
            "status": "idle",
            "door_status": "closed",
            "destinations": []
        } for i in range(1, NUM_ELEVATORS + 1)
    ]

    # Set initial elevator states on the fakeredis client
    for elevator_id in range(1, NUM_ELEVATORS + 1):
        key = ELEVATOR_STATUS.format(elevator_id)
        initial_state = {
            "id": elevator_id,
            "current_floor": 1,
            "status": "idle",
            "door_status": "closed",
            "destinations": []
        }
        await redis_client.set(key, json.dumps(initial_state))

    # Patch the get_redis_client dependency in your app
    with patch('src.config.get_redis_client', return_value=redis_client):
        response = await async_client.get("/api/elevators")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "elevators" in data
    assert len(data["elevators"]) == NUM_ELEVATORS
    for i, elevator in enumerate(data["elevators"], 1):
        assert elevator["id"] == i


@pytest.mark.asyncio
async def test_with_real_redis_setup(async_client, scheduler_with_mock_elevators):
    """Example test using the scheduler fixture that sets up real Redis data."""
    redis_client = scheduler_with_mock_elevators

    # Your app should be able to read the data set up by the fixture
    with patch('src.config.get_redis_client', return_value=redis_client):
        response = await async_client.get("/api/elevators")

    assert response.status_code == 200
    # Add more assertions based on your expected response
