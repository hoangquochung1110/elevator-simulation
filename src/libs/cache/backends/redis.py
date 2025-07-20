"""
Redis cache backend implementation.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, TypeVar

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from src.libs.cache.exceptions import CacheConnectionError, CacheError

from . import BaseCacheBackend

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RedisBackend(BaseCacheBackend):
    """Redis cache backend implementation."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: Optional[float] = 5.0,
        socket_connect_timeout: Optional[float] = 5.0,
        socket_keepalive: Optional[bool] = True,
        socket_keepalive_options: Optional[Dict] = None,
        max_connections: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Redis backend.

        Args:
            host: Redis server host.
            port: Redis server port.
            db: Database number.
            password: Redis password.
            socket_timeout: Socket timeout in seconds.
            socket_connect_timeout: Socket connect timeout in seconds.
            socket_keepalive: Whether to use keepalive.
            socket_keepalive_options: Keepalive options.
            max_connections: Maximum number of connections in the pool.
            **kwargs: Additional Redis client arguments.
        """
        self._client: Optional[Redis] = None
        self._client_params = {
            "host": host or os.environ.get("REDIS_HOST", "localhost"),
            "port": port or int(os.environ.get("REDIS_PORT", 6379)),
            "db": db,
            "password": password,
            "socket_timeout": socket_timeout,
            "socket_connect_timeout": socket_connect_timeout,
            "socket_keepalive": socket_keepalive,
            "socket_keepalive_options": socket_keepalive_options or {},
            "max_connections": max_connections,
            "decode_responses": True,
            **kwargs,
        }

    @property
    def client(self) -> Redis:
        """Get the Redis client, initializing it if necessary."""
        if self._client is None:
            self._client = Redis(**self._client_params)
        return self._client

    async def _ensure_connected(self) -> None:
        """Ensure the Redis client is connected."""
        if self._client is None:
            self._client = Redis(**self._client_params)
        try:
            await self._client.ping()
        except RedisConnectionError as e:
            logger.error("Redis connection error: %s", e)
            raise CacheConnectionError(f"Redis connection error: {e}") from e

    async def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the cache by key."""
        try:
            await self._ensure_connected()
            value = await self.client.get(key)
            if value is None:
                return default
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except RedisConnectionError as e:
            logger.error("Redis get error: %s", e)
            return default

    async def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set a value in the cache."""
        try:
            await self._ensure_connected()
            if not isinstance(value, (str, int, float, bool, bytes)):
                value = json.dumps(value)

            kwargs = {}
            if timeout is not None:
                kwargs["ex"] = timeout
            if nx:
                kwargs["nx"] = True
            if xx:
                kwargs["xx"] = True

            return await self.client.set(key, value, **kwargs)
        except (RedisConnectionError, TypeError) as e:
            logger.error("Redis set error: %s", e)
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        try:
            await self._ensure_connected()
            result = await self.client.delete(key)
            return bool(result)
        except RedisConnectionError as e:
            logger.error("Redis delete error: %s", e)
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        try:
            await self._ensure_connected()
            return bool(await self.client.exists(key))
        except RedisConnectionError as e:
            logger.error("Redis exists error: %s", e)
            return False

    async def close(self) -> None:
        """Close the connection to the cache backend."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get the time-to-live for a key in seconds."""
        try:
            await self._ensure_connected()
            ttl = await self.client.ttl(key)
            return ttl if ttl >= 0 else None
        except RedisConnectionError as e:
            logger.error("Redis TTL error: %s", e)
            return None

    async def set_ttl(self, key: str, timeout: int) -> bool:
        """Set the time-to-live for a key in seconds."""
        try:
            await self._ensure_connected()
            return await self.client.expire(key, timeout)
        except RedisConnectionError as e:
            logger.error("Redis set TTL error: %s", e)
            return False

    async def clear(self) -> None:
        """Clear the entire cache."""
        try:
            await self._ensure_connected()
            await self.client.flushdb()
        except RedisConnectionError as e:
            logger.error("Redis clear error: %s", e)
            raise CacheError(f"Failed to clear cache: {e}") from e

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching a pattern.

        Args:
            pattern: Pattern to match keys against.

        Returns:
            List of matching keys.
        """
        try:
            await self._ensure_connected()
            return [key.decode() for key in await self.client.keys(pattern)]
        except RedisConnectionError as e:
            logger.error("Redis keys error: %s", e)
            return []

    async def ping(self) -> bool:
        """Ping the Redis server.

        Returns:
            bool: True if the server is reachable, False otherwise.
        """
        try:
            await self._ensure_connected()
            return await self.client.ping()
        except RedisConnectionError:
            return False
