import json

from src.config import NUM_ELEVATORS
from src.models.request import Direction, ExternalRequest, InternalRequest
from src.scheduler.scheduler import Scheduler


async def test_scheduler_handles_external_request(
    mock_scheduler_cache, mock_scheduler_pubsub
):
    # Arrange
    scheduler = Scheduler(id="test-1")

    # Mock cache.get to return initial elevator states for all NUM_ELEVATORS
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
    mock_scheduler_cache.get.side_effect = mock_elevator_states
    mock_scheduler_cache.set.return_value = None  # Mock set as well

    # Mock pubsub.publish
    mock_scheduler_pubsub.publish.return_value = None

    await scheduler._load_elevator_states()

    request = ExternalRequest(floor=3, direction=Direction.UP)

    # Act
    await scheduler._handle_external_request(request)

    # Assert
    mock_scheduler_pubsub.publish.assert_called_once()


async def test_scheduler_handles_internal_request(
    mock_scheduler_cache, mock_scheduler_pubsub
):
    # Arrange
    scheduler = Scheduler(id="test-1")

    # Mock cache.get to return initial elevator states for all NUM_ELEVATORS
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
    mock_scheduler_cache.get.side_effect = mock_elevator_states
    mock_scheduler_cache.set.return_value = None  # Mock set as well

    # Mock pubsub.publish
    mock_scheduler_pubsub.publish.return_value = None

    await scheduler._load_elevator_states()

    request = InternalRequest(elevator_id=1, destination_floor=5)

    # Act
    await scheduler._handle_internal_request(request)

    # Assert
    mock_scheduler_pubsub.publish.assert_called_once()
    args, kwargs = mock_scheduler_pubsub.publish.call_args
    assert args[0] == f"elevator:commands:{request.elevator_id}"
    published_command = json.loads(args[1])
    assert published_command["command"] == "add_destination"
    assert published_command["floor"] == 5


async def test_scheduler_calculates_correct_scores(mock_scheduler_cache):
    # Arrange
    scheduler = Scheduler(id="test-1")

    # Set up elevator states for the mock cache
    mock_scheduler_cache.get.side_effect = [
        # State for elevator 1
        {
            "id": 1,
            "current_floor": 1,
            "status": "idle",
            "door_status": "closed",
            "destinations": [],
        },
        # State for elevator 2
        {
            "id": 2,
            "current_floor": 5,
            "status": "moving_up",
            "door_status": "closed",
            "destinations": [6],
        },
        # State for elevator 3
        {
            "id": 3,
            "current_floor": 10,
            "status": "idle",
            "door_status": "closed",
            "destinations": [],
        },
    ]
    mock_scheduler_cache.set.return_value = None

    await scheduler._load_elevator_states()

    request = ExternalRequest(floor=2, direction=Direction.UP)

    # Act
    elevator_id = await scheduler._select_best_elevator_for_external(request)

    # Assert - Should select elevator 1 as it's idle and closer
    assert elevator_id == 1

    # Test another scenario
    request = ExternalRequest(floor=6, direction=Direction.UP)
    elevator_id = await scheduler._select_best_elevator_for_external(request)

    # Assert - Should select elevator 2 as it's on the way
    assert elevator_id == 2
