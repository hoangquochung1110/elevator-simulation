import json
import asyncio
from .config import redis_client
import sys
from .channels import (
    ELEVATOR_REQUESTS,
    ELEVATOR_COMMANDS,
    ELEVATOR_STATUS,
    ELEVATOR_SYSTEM,
)

async def publish(channel: str, message):
    payload = message if isinstance(message, str) else json.dumps(message)
    await redis_client.publish(channel, payload)
    print(f"> published to {channel}: {payload}")


if __name__ == "__main__":
    channel = sys.argv[1] if len(sys.argv) > 1 else ELEVATOR_SYSTEM
    raw = sys.argv[2] if len(sys.argv) > 2 else '"ping"'
    # try to parse JSON, else treat as string
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        msg = raw
    asyncio.run(publish(channel, msg))
