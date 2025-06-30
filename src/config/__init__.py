import asyncio
import os

import structlog
from dotenv import load_dotenv

from .channels import *
from .logging import configure_logging
from .redis import close_redis_client, get_redis_client

# Initialize logger at module level
logger = structlog.get_logger(__name__)

load_dotenv()


# Building configuration
NUM_FLOORS = 10
NUM_ELEVATORS = 3

REDIS_HOST = os.getenv('REDIS_HOST', 'redis-pubsub-101-alb-1732433117.ap-southeast-1.elb.amazonaws.com')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
