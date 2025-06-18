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
                 cluster_mode: bool = False,
                 **kwargs):
        """
        Initialize Redis client with support for both single instance and cluster.

        Args:
            host: Redis host or list of cluster nodes
            port: Redis port
            password: Redis password
            cluster_mode: Whether to use cluster mode
            **kwargs: Additional Redis client arguments
        """
        self.cluster_mode = cluster_mode
        self.client = None
        self.host = host
        self.port = port
        self.password = password
        self.kwargs = kwargs

    async def initialize(self) -> None:
        """Initialize the Redis client based on configuration."""
        try:
            if self.cluster_mode:
                # For cluster mode, we need a list of nodes
                nodes = [{"host": self.host, "port": self.port}]
                self.client = RedisCluster(
                    startup_nodes=nodes,
                    password=self.password,
                    decode_responses=True,
                    retry=Retry(max_attempts=3),
                    **self.kwargs
                )
            else:
                self.client = Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    decode_responses=True,
                    **self.kwargs
                )
            # Test connection
            await self.client.ping()
            logger.info(
                "redis_client_initialized",
                mode="cluster" if self.cluster_mode else "single",
                host=self.host,
                port=self.port
            )
        except Exception as e:
            logger.error(
                "redis_client_initialization_failed",
                error=str(e),
                mode="cluster" if self.cluster_mode else "single",
                exc_info=True
            )
            raise

    @with_retry(retries=3)
    async def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel with retry logic."""
        return await self.client.publish(channel, message)

    @with_retry(retries=3)
    async def xadd(self, stream: str, fields: dict, **kwargs) -> str:
        """Add a message to a stream with retry logic."""
        return await self.client.xadd(stream, fields, **kwargs)

    @with_retry(retries=3)
    async def xreadgroup(self, **kwargs) -> list:
        """Read from a stream within a consumer group with retry logic."""
        return await self.client.xreadgroup(**kwargs)

    @with_retry(retries=3)
    async def xgroup_create(self, stream: str, group: str, **kwargs) -> bool:
        """Create a consumer group with retry logic."""
        try:
            return await self.client.xgroup_create(stream, group, **kwargs)
        except RedisError as e:
            if "BUSYGROUP" not in str(e):
                raise
            return False

    @with_retry(retries=3)
    async def get(self, key: str) -> Optional[str]:
        """Get a value by key with retry logic."""
        return await self.client.get(key)

    @with_retry(retries=3)
    async def set(self, key: str, value: str, **kwargs) -> bool:
        """Set a key-value pair with retry logic."""
        return await self.client.set(key, value, **kwargs)

    async def pubsub(self) -> Any:
        """Get a pubsub interface."""
        return self.client.pubsub()

    async def close(self) -> None:
        """Close the Redis client connection."""
        if self.client:
            await self.client.close()