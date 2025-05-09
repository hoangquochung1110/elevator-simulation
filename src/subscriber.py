import asyncio
import json
import time

from redis import exceptions

from .channels import ELEVATOR_REQUESTS_STREAM, ELEVATOR_STATUS
from .config import NUM_ELEVATORS, redis_client


async def subscribe(*channels: list[str]):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(*channels)
    print(f"✅ subscribed to {channels}")
    async for msg in pubsub.listen():
        if msg.get("type") == "message":
            await handle_message(msg["data"])

async def consume(stream, group, consumer_id):

    try:
        # create group
        created = await redis_client.xgroup_create(
            stream,
            group,
            id="$",
            mkstream=True,
        )
    except exceptions.ResponseError as e:
        # Group already exists
        print(f"✅ Group already exists: {group}")
    else:
        print(f"✅ {created} stream: {stream}, group: {group}")
    # Main consumer loop
    while True:
        # Read new messages for this consumer
        messages = await redis_client.xreadgroup(
            groupname=group,
            consumername=consumer_id,
            streams={stream: '>'},  # '>' means new messages only
            count=10,  # Process up to 10 messages at a time
            block=2000  # Block for 2000ms if no messages available
        )
        if not messages:
            continue

        # Process messages
        for stream, message_list in messages:
            for message_id, message_data in message_list:
                try:
                    await handle_message(message_data)
                    # Acknowledge the message when done
                    await redis_client.xack(stream, group, message_id)
                except Exception as e:
                    print(f"Error processing message {message_id}: {e}")
                    # Failed message will remain pending for other consumers

        await asyncio.sleep(0.1)   # Small pause between polling


async def handle_message(message: str | dict):
    if isinstance(message, dict):
        data = message
    else:  # message is a string
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            data = message
    print(f"< received: {data}")
    # ← your business logic here


async def main():
    # Create tasks for both pub/sub and streams
    tasks = []

    # Add stream and command consumer tasks
    stream_task = asyncio.create_task(
        consume(ELEVATOR_REQUESTS_STREAM, "stream-group", "consumer-1"),
    )
    tasks.append(stream_task)

    # Add pub/sub subscription tasks
    channels = [ELEVATOR_STATUS.format(i) for i in range(1, NUM_ELEVATORS + 1)]

    pubsub_task = asyncio.create_task(subscribe(*channels))
    tasks.append(pubsub_task)

    # Run both concurrently and wait for both to complete
    # (They should run forever unless there's an error)
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Redis connection will be closed automatically when the event loop exits
        pass
