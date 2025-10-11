"""
Cache package for Redis-based caching with a Django-like interface.

This package provides a high-level interface for caching operations,
with Redis as the default backend. It's designed to be simple to use
while providing powerful features like key-based caching, timeouts,
and decorator-based caching.

Basic usage:
    >>> from src.libs.cache import cache
    >>> 
    >>> # Set a value
    >>> await cache.set('my_key', 'my_value', timeout=60)
    >>> 
    >>> # Get a value
    >>> value = await cache.get('my_key')
    >>> 
    >>> # Using the cached decorator
    >>> @cache.cached(timeout=60)
    ... async def expensive_operation(param):
    ...     # Some expensive operation
    ...     return result
"""

__version__ = "0.1.0"

from .service import CacheService, get_cache, init_cache, close
from .exceptions import (
    CacheError,
    CacheMissError,
    CacheConnectionError,
    CacheTimeoutError,
    CacheLockError,
)

# The global cache instance
cache = get_cache()

__all__ = [
    # Main cache instance
    'cache',
    
    # Service and initialization
    'CacheService',
    'get_cache',
    'init_cache',
    'close',
    
    # Exceptions
    'CacheError',
    'CacheMissError',
    'CacheConnectionError',
    'CacheTimeoutError',
    'CacheLockError',
]
