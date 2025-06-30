"""
Redis adapter module that provides a unified interface for both single instance
and cluster Redis deployments.
"""
import asyncio
import os
from functools import wraps
from typing import Any, Callable, Concatenate, Optional, ParamSpec, TypeVar

import structlog
from redis.asyncio import Redis, RedisCluster
from redis.exceptions import ConnectionError, RedisClusterException, RedisError
from redis.retry import Retry

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

def with_retry(retries: int = 3, backoff: float = 1.5) -> Callable:
    """Decorator that adds retry logic with exponential backoff."""
    def decorator(func: Callable[Concatenate[Any, P], T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(self: Any, *args: P.args, **kwargs: P.kwargs) -> T:
            last_error = None
            for attempt in range(retries):
                try:
                    return await func(self, *args, **kwargs)
                except (ConnectionError, RedisClusterException) as e:
                    last_error = e
                    if attempt < retries - 1:
                        delay = backoff ** attempt
                        logger.warning(
                            "redis_operation_retry",
                            operation=func.__name__,
                            attempt=attempt + 1,
                            delay=delay,
                            error=str(e)
                        )
                        await asyncio.sleep(delay)
                    continue
            raise last_error
        return wrapper
    return decorator

class RedisAdapter:
    """
    Adapter class that provides a unified interface for Redis operations,
    supporting both single instance and cluster deployments.
    """
    def __init__(self,
                 host: str = "redis",
                 port: int = 6379,
                 password: Optional[str] = None,
                 db: int = 0,
                 cluster_mode: bool = False,
                 decode_responses: bool = True,
                 **kwargs):
        """
        Initialize Redis client with support for both single instance and cluster.

        Args:
            host: Redis host or list of cluster nodes
            port: Redis port
            password: Redis password
            db: Redis database number
            cluster_mode: Whether to use cluster mode
            decode_responses: Whether to decode responses to strings
            **kwargs: Additional Redis client arguments
        """
        self.cluster_mode = cluster_mode
        self.client = None
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self.kwargs = kwargs
        self.logger = structlog.get_logger(__name__)

    async def _create_single_client(self):
        """Create a single Redis client instance."""
        return Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=self.decode_responses,
            **self.kwargs
        )

    async def _create_cluster_client(self):
        """Create a Redis cluster client instance."""
        nodes = [{"host": self.host, "port": self.port}]
        return RedisCluster(
            startup_nodes=nodes,
            password=self.password,
            decode_responses=self.decode_responses,
            retry=Retry(max_attempts=3),
            **self.kwargs
        )

    async def initialize(self):
        """Initialize the Redis client connection."""
        try:
            if self.cluster_mode:
                self.client = await self._create_cluster_client()
            else:
                self.client = await self._create_single_client()

            # Test connection
            await self.client.ping()

            # Log successful initialization
            self.logger.info(
                "redis_client_initialized",
                mode="cluster" if self.cluster_mode else "single",
                host=self.host,
                port=self.port,
                db=getattr(self, 'db', 0)
            )

        except Exception as e:
            self.logger.error(
                "redis_client_initialization_failed",
                error=str(e),
                mode="cluster" if self.cluster_mode else "single",
                host=self.host,
                port=self.port,
                db=getattr(self, 'db', 0),
                exc_info=True
            )
            raise

    # @with_retry(retries=3)
    # async def publish(self, channel: str, message: str) -> int:
    #     """Publish a message to a channel with retry logic.

    #     Args:
    #         channel: Name of the channel to publish to
    #         message: Message to publish

    #     Returns:
    #         Number of clients that received the message
    #     """
    #     return await self.client.publish(channel, message)

    # @with_retry(retries=3)
    # async def xadd(self, stream: str, fields: dict, **kwargs) -> str:
    #     """Add a message to a stream with retry logic."""
    #     return await self.client.xadd(stream, fields, **kwargs)

    # @with_retry(retries=3)
    # async def xreadgroup(self, **kwargs) -> list:
    #     """Read from a stream within a consumer group with retry logic."""
    #     return await self.client.xreadgroup(**kwargs)

    # @with_retry(retries=3)
    # async def xgroup_create(self, stream: str, group: str, **kwargs) -> bool:
    #     """Create a consumer group with retry logic."""
    #     try:
    #         return await self.client.xgroup_create(stream, group, **kwargs)
    #     except RedisError as e:
    #         if "BUSYGROUP" not in str(e):
    #             raise
    #         return False


    async def close(self) -> None:
        """Close the Redis client connection."""
        if self.client:
            await self.client.close()