from src.config import ELEVATOR_REQUESTS_STREAM, NUM_ELEVATORS


async def test_index_route(async_client):
    """Test the index route synchronously."""
    response = await async_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


async def test_create_internal_request(async_client, mock_app_event_stream):
    """Test internal request creation asynchronously."""
    # Mock the publish operation
    mock_app_event_stream.publish.return_value = b"test-id"

    # Arrange
    request_data = {"elevator_id": 1, "destination_floor": 5}

    # Make request (dependency injection is handled by the fixture)
    response = await async_client.post("/api/requests/internal", json=request_data)

    # Assert
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["channel"] == ELEVATOR_REQUESTS_STREAM


async def test_get_elevator_states(async_client, mock_app_cache):
    """Test elevator states retrieval asynchronously."""

    # Setup test data to be returned by the mock
    mock_elevator_states = [
        {
            "id": i,
            "current_floor": 1,
            "status": "idle",
            "door_status": "closed",
            "destinations": [],
        }
        for i in range(1, NUM_ELEVATORS + 1)
    ]
    mock_app_cache.get.side_effect = mock_elevator_states

    # Make request
    response = await async_client.get("/api/elevators")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "elevators" in data
    assert len(data["elevators"]) == NUM_ELEVATORS
    for i, elevator in enumerate(data["elevators"], 1):
        assert elevator["id"] == i
