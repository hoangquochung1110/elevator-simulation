import asyncio
import json

import pytest

from src.config import ELEVATOR_REQUESTS_STREAM


@pytest.mark.asyncio
async def test_stream_create_group(redis_client):
    """Test creating a consumer group for a stream."""
    group_name = "test-group"

    # Create consumer group
    created = await redis_client.xgroup_create(
        ELEVATOR_REQUESTS_STREAM,
        group_name,
        id="$",
        mkstream=True
    )
    assert created is True

    # Try creating same group again should raise
    with pytest.raises(Exception):
        await redis_client.xgroup_create(
            ELEVATOR_REQUESTS_STREAM,
            group_name,
            id="$",
            mkstream=True
        )

@pytest.mark.asyncio
async def test_stream_consumer_group(redis_client):
    """Test consuming messages from a stream using a consumer group."""
    group_name = "test-group"
    consumer_name = "test-consumer"
    test_message = {"request": "test"}

    # Create consumer group
    try:
        await redis_client.xgroup_create(
            ELEVATOR_REQUESTS_STREAM,
            group_name,
            id="$",
            mkstream=True
        )
    except:
        # Group might already exist
        pass

    # Add a message to the stream
    message_id = await redis_client.xadd(
        ELEVATOR_REQUESTS_STREAM,
        test_message
    )

    # Read message using the consumer group
    messages = await redis_client.xreadgroup(
        groupname=group_name,
        consumername=consumer_name,
        streams={ELEVATOR_REQUESTS_STREAM: '>'},
        count=1
    )

    assert messages
    assert len(messages) == 1
    stream_name, stream_messages = messages[0]
    assert stream_name == ELEVATOR_REQUESTS_STREAM
    assert len(stream_messages) == 1
    msg_id, msg_data = stream_messages[0]
    assert msg_data == test_message

    # Acknowledge the message
    await redis_client.xack(ELEVATOR_REQUESTS_STREAM, group_name, msg_id)

    # Verify message was acknowledged
    pending = await redis_client.xpending(ELEVATOR_REQUESTS_STREAM, group_name)
    assert pending["pending"] == 0

@pytest.mark.asyncio
async def test_stream_multiple_consumers(redis_client):
    """Test multiple consumers reading from the same consumer group."""
    group_name = "multi-consumer-group"
    consumers = ["consumer1", "consumer2"]
    test_messages = [
        {"request": "test1"},
        {"request": "test2"}
    ]

    # Setup consumer group
    try:
        await redis_client.xgroup_create(
            ELEVATOR_REQUESTS_STREAM,
            group_name,
            id="$",
            mkstream=True
        )
    except:
        pass

    # Add messages to stream
    for msg in test_messages:
        await redis_client.xadd(ELEVATOR_REQUESTS_STREAM, msg)

    # Read messages with different consumers
    received_messages = []
    for consumer in consumers:
        messages = await redis_client.xreadgroup(
            groupname=group_name,
            consumername=consumer,
            streams={ELEVATOR_REQUESTS_STREAM: '>'},
            count=1
        )
        if messages:
            stream_name, stream_messages = messages[0]
            msg_id, msg_data = stream_messages[0]
            received_messages.append(msg_data)
            await redis_client.xack(ELEVATOR_REQUESTS_STREAM, group_name, msg_id)

    # Verify each message was received exactly once
    assert len(received_messages) == len(test_messages)
    for msg in test_messages:
        assert msg in received_messages
