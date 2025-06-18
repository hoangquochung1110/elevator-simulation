import asyncio
import json

import pytest

from src.config import ELEVATOR_STATUS, NUM_ELEVATORS


@pytest.mark.asyncio
async def test_publish_message(redis_client):
    """Test publishing a message to a Redis channel."""
    channel = ELEVATOR_STATUS.format(1)
    test_message = {"status": "test"}

    # Create a pubsub instance for listening
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    # Publish the message
    payload = json.dumps(test_message)
    await redis_client.publish(channel, payload)

    # Wait for and verify the message
    message = await pubsub.get_message(timeout=1)  # Subscribe confirmation
    message = await pubsub.get_message(timeout=1)  # Actual message

    assert message is not None
    assert message["type"] == "message"
    assert message["channel"] == channel
    assert json.loads(message["data"]) == test_message

    await pubsub.unsubscribe()

@pytest.mark.asyncio
async def test_multiple_elevator_channels(redis_client):
    """Test publishing to multiple elevator status channels."""
    channels = [ELEVATOR_STATUS.format(i) for i in range(1, NUM_ELEVATORS + 1)]
    test_message = "ping"

    # Subscribe to all channels
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(*channels)

    # Get subscription confirmation messages
    for _ in channels:
        await pubsub.get_message(timeout=1)

    # Publish to all channels
    for channel in channels:
        await redis_client.publish(channel, test_message)

    # Verify messages on all channels
    received_messages = []
    for _ in channels:
        message = await pubsub.get_message(timeout=1)
        assert message is not None
        assert message["type"] == "message"
        received_messages.append(message)

    assert len(received_messages) == len(channels)
    for msg, channel in zip(received_messages, channels):
        assert msg["channel"] == channel
        assert msg["data"] == test_message

    await pubsub.unsubscribe()

@pytest.mark.asyncio
async def test_message_format(redis_client):
    """Test different message formats (string vs dict) in pub/sub."""
    channel = ELEVATOR_STATUS.format(1)
    test_messages = [
        {"status": "test", "floor": 1},  # dict
        "test message",  # string
        '{"status": "test"}'  # JSON string
    ]

    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    await pubsub.get_message(timeout=1)  # Subscribe confirmation

    for msg in test_messages:
        payload = msg if isinstance(msg, str) else json.dumps(msg)
        await redis_client.publish(channel, payload)

        received = await pubsub.get_message(timeout=1)
        assert received is not None
        assert received["type"] == "message"
        assert received["channel"] == channel

        if isinstance(msg, dict):
            assert json.loads(received["data"]) == msg
        else:
            assert received["data"] == msg

    await pubsub.unsubscribe()
