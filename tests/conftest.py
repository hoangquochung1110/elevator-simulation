import asyncio
import json
from typing import AsyncGenerator, Callable, Dict
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.app.main import app
from src.config import (
    ELEVATOR_REQUESTS_STREAM,
    ELEVATOR_STATUS,
    NUM_ELEVATORS,
    get_redis_client,
)

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest_asyncio.fixture
async def async_client():
    """Create an async client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def redis_client():
    """Create a FakeRedis client for testing (the same one the app uses)."""
    from fakeredis import FakeAsyncRedis

    redis_client = FakeAsyncRedis(decode_responses=True)
    return redis_client


@pytest_asyncio.fixture(autouse=True)
async def app_dependencies(redis_client, mock_app_cache, mock_app_event_stream):
    """
    General purpose fixture for managing FastAPI dependency overrides.
    This fixture can be used to override any dependency in the FastAPI app.
    Dependencies will be automatically cleaned up after the test.

    Note:
        Using function scope ensures a fresh Redis client for each test.
        The autouse=True ensures proper dependency injection for all tests.

    Reference docs: https://fastapi.tiangolo.com/advanced/testing-dependencies/#use-the-appdependency_overrides-attribute
    """
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides = {}

    try:
        pass
    except KeyError:
        pass
    else:
        yield app.dependency_overrides
    finally:
        app.dependency_overrides = original_overrides


@pytest_asyncio.fixture
async def elevators(redis_client):
    """Setup initial elevator states in Redis with proper dependency injection."""
    # Setup initial elevator states
    for elevator_id in range(1, NUM_ELEVATORS + 1):
        elevator_state = {
            "id": elevator_id,
            "current_floor": 1,
            "status": "idle",
            "door_status": "closed",
            "destinations": [],
        }
        await redis_client.set(
            ELEVATOR_STATUS.format(elevator_id), json.dumps(elevator_state)
        )
    yield redis_client


@pytest_asyncio.fixture
async def event_loop():
    """Create a new event loop for each test."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)

    yield loop

    try:
        # Cancel all running tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Wait for tasks to complete cancellation
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    except Exception:
        pass
    finally:
        try:
            loop.close()
        except Exception:
            pass


@pytest.fixture
def mock_app_cache(mocker):
    """Mocks the cache for the application."""
    return mocker.patch("src.app.main.cache", new_callable=AsyncMock)


@pytest.fixture
def mock_app_event_stream(mocker):
    """Mocks the event stream for the application."""
    return mocker.patch("src.app.main.event_stream", new_callable=AsyncMock)


@pytest.fixture
def mock_scheduler_cache(mocker):
    """Mocks the cache for the scheduler."""
    return mocker.patch("src.scheduler.scheduler.cache", new_callable=AsyncMock)


@pytest.fixture
def mock_scheduler_event_stream(mocker):
    """Mocks the event stream for the scheduler."""
    return mocker.patch("src.scheduler.scheduler.event_stream", new_callable=AsyncMock)


@pytest.fixture
def mock_scheduler_pubsub(mocker):
    """Mocks the pubsub for the scheduler."""
    return mocker.patch("src.scheduler.scheduler.pubsub", new_callable=AsyncMock)


@pytest.fixture
def mock_controller_cache(mocker):
    """Mocks the cache for the controller."""
    return mocker.patch("src.controller.controller.cache", new_callable=AsyncMock)


@pytest.fixture
def mock_controller_pubsub(mocker):
    """Mocks the pubsub for the controller."""
    mock_pubsub_instance = AsyncMock()
    mock_pubsub_instance.subscribe = AsyncMock()
    mock_pubsub_instance.unsubscribe = AsyncMock()
    mock_pubsub_instance.close = AsyncMock()
    mock_pubsub_instance.publish = AsyncMock()
    mock_pubsub_instance._backend = AsyncMock()
    mock_pubsub_instance._backend._pubsub = AsyncMock()
    mock_pubsub_instance._backend._pubsub.get_message = AsyncMock()
    mock_pubsub_instance._backend._ensure_connected = AsyncMock()

    mocker.patch(
        "src.controller.controller.get_local_pubsub", return_value=mock_pubsub_instance
    )
    return mock_pubsub_instance
