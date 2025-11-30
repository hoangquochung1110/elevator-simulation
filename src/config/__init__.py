import os

import logging
from dotenv import load_dotenv

from .channels import (
    ELEVATOR_COMMANDS,
    ELEVATOR_REQUESTS_STREAM,
    ELEVATOR_STATUS,
)
from .redis import close_redis_client, get_redis_client

# Initialize logger at module level
logger = logging.getLogger(__name__)

load_dotenv()


# Building configuration
NUM_FLOORS = 10
NUM_ELEVATORS = 3

REDIS_HOST = os.getenv(
    "REDIS_HOST",
    "redis-pubsub-101-alb-1732433117.ap-southeast-1.elb.amazonaws.com",
)
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

__all__ = [
    "ELEVATOR_COMMANDS",
    "ELEVATOR_REQUESTS_STREAM",
    "ELEVATOR_STATUS",
    "close_redis_client",
    "get_redis_client",
    "NUM_FLOORS",
    "NUM_ELEVATORS",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_PASSWORD",
    "REDIS_DB",
]
