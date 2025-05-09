import asyncio
import json

from .channels import ELEVATOR_STATUS
from .config import NUM_ELEVATORS, redis_client


async def publish(channel: str, message):
    """
    Publish a message to a Redis channel.

    Args:
        channel (str): The Redis channel to publish to
        message (str | dict): The message to publish
    """
    payload = message if isinstance(message, str) else json.dumps(message)
    await redis_client.publish(channel, payload)
    print(f"> published to {channel}: {payload}")


async def main():
    """
    Main entry point for the publisher.
    Publishes a message to all elevator status channels.
    """
    raw = '"ping"'
    channels = [ELEVATOR_STATUS.format(i) for i in range(1, NUM_ELEVATORS + 1)]
    tasks = []

    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        msg = raw

    for channel in channels:
        tasks.append(publish(channel, msg))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("✅ Event loop completed")
        # Redis connection will be closed automatically when the event loop exits
