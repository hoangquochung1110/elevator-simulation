"""
Cache service implementation.

This module provides a high-level interface for caching operations,
with Redis as the default backend.
"""
import functools
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from .backends import BaseCacheBackend
from .backends.redis import RedisBackend

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheService:
    """High-level cache service with a simple interface.

    This class provides a thread-safe, high-level interface to the cache backend.
    It handles serialization, error handling, and provides utility methods.
    """

    _instance = None
    _backend: BaseCacheBackend = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern."""
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        backend: Optional[Union[str, BaseCacheBackend]] = None,
        **backend_options
    ) -> None:
        """Initialize the cache service.

        Args:
            backend: Either a backend instance or a string specifying the backend
                    (e.g., 'redis'). If None, RedisBackend will be used.
            **backend_options: Additional options to pass to the backend.
        """
        if self._initialized:
            return

        if backend is None or backend == 'redis':
            self._backend = RedisBackend(**backend_options)
        elif isinstance(backend, str):
            raise ValueError(f"Unsupported cache backend: {backend}")
        elif isinstance(backend, BaseCacheBackend):
            self._backend = backend
        else:
            raise ValueError("Invalid backend type")

        self._initialized = True

    async def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the cache by key."""
        return await self._backend.get(key, default)

    async def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set a value in the cache."""
        return await self._backend.set(key, value, timeout=timeout, nx=nx, xx=xx)

    async def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        return await self._backend.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        return await self._backend.exists(key)

    async def close(self) -> None:
        """Close the connection to the cache backend."""
        if self._backend:
            await self._backend.close()

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Fetch multiple keys from the cache."""
        return await self._backend.get_many(keys)

    async def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None) -> None:
        """Set multiple keys in the cache."""
        await self._backend.set_many(data, timeout=timeout)

    async def delete_many(self, keys: List[str]) -> None:
        """Delete multiple keys from the cache."""
        await self._backend.delete_many(keys)

    async def get_or_set(
        self,
        key: str,
        default: Any,
        timeout: Optional[int] = None,
    ) -> Any:
        """Get a key's value or set it with a default if it doesn't exist."""
        return await self._backend.get_or_set(key, default, timeout=timeout)

    async def incr(self, key: str, delta: int = 1) -> int:
        """Increment a key's value by delta."""
        return await self._backend.incr(key, delta=delta)

    async def decr(self, key: str, delta: int = 1) -> int:
        """Decrement a key's value by delta."""
        return await self._backend.decr(key, delta=delta)

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get the time-to-live for a key in seconds."""
        return await self._backend.get_ttl(key)

    async def set_ttl(self, key: str, timeout: int) -> bool:
        """Set the time-to-live for a key in seconds."""
        return await self._backend.set_ttl(key, timeout)

    async def clear(self) -> None:
        """Clear the entire cache."""
        await self._backend.clear()

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching a pattern."""
        if hasattr(self._backend, 'keys'):
            return await self._backend.keys(pattern)
        raise NotImplementedError("The current backend does not support keys()")

    async def ping(self) -> bool:
        """Ping the cache server."""
        if hasattr(self._backend, 'ping'):
            return await self._backend.ping()
        return True

    def cached(
        self,
        key: Optional[Union[str, Callable[..., str]]] = None,
        timeout: Optional[int] = None,
        unless: Optional[Callable[..., bool]] = None,
    ) -> Callable:
        """Decorator to cache the result of an async function.

        Args:
            key: Cache key (string or callable that generates a key from args/kwargs)
            timeout: Cache timeout in seconds
            unless: Callable that returns True if caching should be skipped

        Example:
            @cache.cached(timeout=60)
            async def get_data():
                # Expensive operation
                return data
        """
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Skip caching if unless returns True
                if unless and unless(*args, **kwargs):
                    return await func(*args, **kwargs)

                # Generate cache key
                if callable(key):
                    cache_key = key(*args, **kwargs)
                elif key is not None:
                    cache_key = key
                else:
                    # Default key is function name + args + kwargs
                    cache_key = f"{func.__module__}:{func.__name__}:{args}:{kwargs}"

                # Try to get from cache
                try:
                    cached = await self.get(cache_key)
                    if cached is not None:
                        return cached
                except Exception as e:
                    logger.warning("Cache get failed: %s", e)

                # Call the function and cache the result
                result = await func(*args, **kwargs)

                try:
                    await self.set(cache_key, result, timeout=timeout)
                except Exception as e:
                    logger.warning("Cache set failed: %s", e)

                return result

            return wrapper
        return decorator


# Global cache instance
_cache_service = None


def get_cache() -> CacheService:
    """Get the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def init_cache(backend=None, **backend_options) -> CacheService:
    """Initialize the global cache service with the given backend."""
    global _cache_service
    _cache_service = CacheService(backend, **backend_options)
    return _cache_service


# Export common functions for convenience
async def get(key: str, default: Any = None) -> Any:
    """Get a value from the cache."""
    return await get_cache().get(key, default)


async def set(
    key: str,
    value: Any,
    timeout: Optional[int] = None,
    nx: bool = False,
    xx: bool = False,
) -> bool:
    """Set a value in the cache."""
    return await get_cache().set(key, value, timeout=timeout, nx=nx, xx=xx)


async def delete(key: str) -> bool:
    """Delete a key from the cache."""
    return await get_cache().delete(key)


async def exists(key: str) -> bool:
    """Check if a key exists in the cache."""
    return await get_cache().exists(key)


async def close() -> None:
    """Close the connection to the cache backend."""
    await get_cache().close()
