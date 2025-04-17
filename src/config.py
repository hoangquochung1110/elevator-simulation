import os
from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv()

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", None),
    decode_responses=True,
)

# Building configuration
NUM_FLOORS = 10
NUM_ELEVATORS = 3

