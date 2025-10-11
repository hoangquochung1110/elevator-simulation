"""
Simplified Redis client initialization.
"""

from typing import Optional
import logging
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)

_redis_client = None

async def get_redis_client(
    host: str,
    port: int,
    db: int = 0,
    password: Optional[str] = None,
    **kwargs
) -> Redis:
    """
    Get a Redis client instance (singleton).

    Args:
        host: Redis server host (required).
        port: Redis server port (required).
        db: Redis database number. Defaults to 0.
        password: Redis password. Required if authentication is needed.
        **kwargs: Additional arguments to pass to Redis constructor.

    Returns:
        Redis: An instance of the Redis client.

    Raises:
        ValueError: If required connection parameters are missing or invalid.
        TypeError: If parameters have incorrect types.
    """
    global _redis_client
    if _redis_client:
        return _redis_client

    # Validate parameter types
    if not isinstance(host, str) or not host:
        raise ValueError("Redis host must be a non-empty string")
    if not isinstance(port, int) or port <= 0 or port > 65535:
        raise ValueError("Redis port must be a valid port number (1-65535)")
    if not isinstance(db, int) or db < 0:
        raise ValueError("Redis database number must be a non-negative integer")

    try:
        logger.info("Initializing Redis client - host: %s, port: %s, db: %s", host, port, db)
        _redis_client = Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            **kwargs
        )
        
        await _redis_client.ping()
        logger.info("Redis client initialized successfully")
        return _redis_client
    except RedisConnectionError as e:
        logger.error(
            "Failed to connect to Redis: %s, host=%s, port=%s",
            str(e), host, port,
            exc_info=True
        )
        raise
    except Exception as e:
        logger.error(
            "An unexpected error occurred during Redis initialization: %s",
            str(e),
            exc_info=True
        )
        raise

async def close_redis_client() -> None:
    """
    Close the shared Redis client connection.
    
    This will close the connection and set the client to None, allowing a new
    connection to be established on the next get_redis_client() call.
    """
    global _redis_client
    if _redis_client:
        try:
            await _redis_client.close()
            logger.info("Redis client connection closed")
        except Exception as e:
            logger.error(
                "Error while closing Redis connection: %s",
                str(e),
                exc_info=True
            )
        finally:
            _redis_client = None
