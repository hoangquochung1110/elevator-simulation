import os

import structlog
from dotenv import load_dotenv
from redis.asyncio import Redis

from .channels import *

load_dotenv()


def configure_logging():
    """
    Set up structured JSON logging for the application using structlog.

    This configures the standard logging module to emit plain messages,
    then initializes structlog with processors to:
      1. Timestamp logs in ISO format.
      2. Include log level and stack information.
      3. Format exception info when present.
      4. Render final output as JSON for easy ingestion into log systems.

    Call this once at startup so all modules use the same logging configuration.
    """
    import logging
    import sys

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # Set appropriate level

    # Create handler that writes to stdout
    handler = logging.StreamHandler(sys.stdout)
    root_logger.addHandler(handler)

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", None),
    decode_responses=True,
)

# Building configuration
NUM_FLOORS = 10
NUM_ELEVATORS = 3
