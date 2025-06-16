import asyncio
import json
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fakeredis.aioredis import FakeRedis

from src.app.main import app
from src.config import ELEVATOR_REQUESTS_STREAM, ELEVATOR_STATUS, NUM_ELEVATORS, get_redis_client

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Add this to pytest.ini or configure here
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(loop_scope="function")
async def async_client():
    """Create an async client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def redis_client():
    """Create a FakeRedis client for testing (the same one the app uses)."""
    client = await get_redis_client()
    await client.flushdb()  # Clean the test database
    yield client
    await client.flushdb()
    await client.close()

@pytest_asyncio.fixture(loop_scope="function")
async def scheduler_with_mock_elevators(redis_client):
    """Setup initial elevator states in Redis."""
    # Setup initial elevator states
    for elevator_id in range(1, NUM_ELEVATORS + 1):
        elevator_state = {
            "id": elevator_id,
            "current_floor": 1,
            "status": "idle",
            "door_status": "closed",
            "destinations": []
        }
        await redis_client.set(
            ELEVATOR_STATUS.format(elevator_id),
            json.dumps(elevator_state)
        )
    return redis_client

@pytest.fixture(scope="function")
def override_redis_dependency():
    """Override Redis dependency in FastAPI app with FakeRedis."""
    try:
        from src.app.main import app
        from src.config import get_redis_client

        async def mock_get_redis_client():
            fake_client = await get_redis_client()
            await fake_client.flushdb()
            yield fake_client

        app.dependency_overrides[get_redis_client] = mock_get_redis_client
        yield
    finally:
        try:
            app.dependency_overrides.clear()
        except:
            pass


# Add event loop fixture to ensure clean event loop per test
@pytest_asyncio.fixture(scope="function")
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
