import asyncio
import os

import structlog
from dotenv import load_dotenv

from .channels import *
from .redis_adapter import RedisAdapter

# Initialize logger at module level
logger = structlog.get_logger(__name__)

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

    This function is idempotent and safe to call multiple times.
    """
    import logging
    import sys

    # Get the root logger
    root_logger = logging.getLogger()

    # Return early if already configured
    if hasattr(configure_logging, '_configured'):
        return

    # Remove all existing handlers to prevent duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure basic logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Configure structlog
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

    # Mark as configured
    configure_logging._configured = True


class RedisClientManager:
    """Manages Redis client lifecycle and configuration.
    
    This class handles the singleton pattern for Redis client instances,
    configuration management, and proper cleanup.
    """
    _instance = None
    _lock = asyncio.Lock()
    _client = None
    _testing = False
    
    @classmethod
    def set_testing_mode(cls, enabled: bool = True) -> None:
        """Enable or disable testing mode.
        
        When testing mode is enabled, a FakeRedis instance will be used.
        
        Args:
            enabled: Whether to enable testing mode
        """
        cls._testing = enabled
    
    @classmethod
    async def get_client(cls) -> 'RedisAdapter.client':
        """Get the Redis client instance, initializing if needed.
        
        This method is thread-safe and ensures only one Redis client is created.
        
        Returns:
            The Redis client instance (Redis, RedisCluster, or FakeRedis)
            
        Raises:
            RuntimeError: If Redis client initialization fails
        """
        if cls._client is not None:
            return cls._client
            
        async with cls._lock:
            if cls._client is not None:
                return cls._client
                
            try:
                if cls._testing or os.getenv("TESTING") == "True":
                    from fakeredis.aioredis import FakeRedis
                    logger.info("Using FakeRedis for testing")
                    cls._client = FakeRedis(decode_responses=True)
                else:
                    adapter = cls._create_adapter()
                    await adapter.initialize()
                    cls._client = adapter.client
                return cls._client
            except Exception as e:
                logger.error(
                    "Failed to initialize Redis client",
                    error=str(e),
                    exc_info=True
                )
                raise RuntimeError("Failed to initialize Redis client") from e
    
    @classmethod
    def _create_adapter(cls) -> 'RedisAdapter':
        """Create a RedisAdapter instance with current configuration."""
        return RedisAdapter(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            password=os.getenv('REDIS_PASSWORD'),
            db=int(os.getenv('REDIS_DB', '0')),
            cluster_mode=os.getenv('REDIS_CLUSTER_MODE', 'false').lower() == 'true',
            decode_responses=True
        )
    
    @classmethod
    async def close(cls) -> None:
        """Close the Redis client connection if it exists."""
        if cls._client is not None:
            await cls._client.close()
            cls._client = None
            logger.debug("Redis client connection closed")
    
    @classmethod
    async def reset(cls) -> None:
        """Reset the client manager (for testing purposes)."""
        await cls.close()
        cls._testing = False

# Public API
get_redis_client = RedisClientManager.get_client
set_redis_testing_mode = RedisClientManager.set_testing_mode

# Building configuration
NUM_FLOORS = 10
NUM_ELEVATORS = 3
