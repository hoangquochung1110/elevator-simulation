import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from src.app.main import app
from src.config import (ELEVATOR_REQUESTS_STREAM, ELEVATOR_STATUS,
                        NUM_ELEVATORS, get_redis_client)
from src.models.elevator import ElevatorStatus
from src.models.request import Direction


async def test_index_route(async_client):
    """Test the index route synchronously."""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_create_internal_request(async_client, redis_client):
    """Test internal request creation asynchronously."""
    # Mock the xadd operation
    redis_client.xadd = AsyncMock(return_value=b"test-id")

    # Arrange
    request_data = {
        "elevator_id": 1,
        "destination_floor": 5
    }

    # Make request (dependency injection is handled by the fixture)
    response = await async_client.post("/api/requests/internal", json=request_data)

    # Assert
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["channel"] == ELEVATOR_REQUESTS_STREAM


async def test_get_elevator_states(async_client, redis_client):
    """Test elevator states retrieval asynchronously."""

    # Setup test data
    for i in range(1, NUM_ELEVATORS + 1):
        key = ELEVATOR_STATUS.format(i)
        test_state = {
            "id": i,
            "current_floor": 1,
            "status": "idle",
            "door_status": "closed",
            "destinations": []
        }
        await redis_client.set(key, json.dumps(test_state))

    # Make request (dependency injection is handled by the fixture)
    response = await async_client.get("/api/elevators")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "elevators" in data
    assert len(data["elevators"]) == NUM_ELEVATORS
    for i, elevator in enumerate(data["elevators"], 1):
        assert elevator["id"] == i
        assert elevator["current_floor"] == 1
        assert elevator["status"] == "idle"
        assert elevator["door_status"] == "closed"
        assert elevator["destinations"] == []


async def test_with_real_redis_setup(async_client):
    """Test using the Redis fixture with actual data setup."""
    response = await async_client.get("/api/elevators")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "elevators" in data
