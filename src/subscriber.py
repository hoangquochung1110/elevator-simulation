import json
import sys
import asyncio

from .config import redis_client
from .channels import (
    ELEVATOR_REQUESTS,
    ELEVATOR_COMMANDS,
    ELEVATOR_STATUS,
    ELEVATOR_SYSTEM,
)

async def subscribe(*channels: list[str]):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(*channels)
    print(f"✅ subscribed to {channels}")
    async for msg in pubsub.listen():
        if msg.get("type") == "message":
            await handle_message(channels, msg["data"])


async def handle_message(channels: str, message: str):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        data = message
    print(f"< received: {data}")
    # ← your business logic here


if __name__ == "__main__":
    # usage: python src/subscriber.py my-channel
    channels = []
    if len(sys.argv) > 1:
        channels = sys.argv[1:]
    else:
        channels = [
            ELEVATOR_REQUESTS,
            ELEVATOR_COMMANDS,
            ELEVATOR_STATUS,
            ELEVATOR_SYSTEM,
        ]
    asyncio.run(subscribe(*channels))
