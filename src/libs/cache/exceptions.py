"""
Custom exceptions for the cache service.
"""


class CacheError(Exception):
    """Base exception for all cache-related errors."""

    pass


class CacheMissError(CacheError):
    """Raised when a requested key is not found in the cache."""

    pass


class CacheConnectionError(CacheError):
    """Raised when there's an error connecting to the cache backend."""

    pass


class CacheTimeoutError(CacheError):
    """Raised when a cache operation times out."""

    pass


class CacheLockError(CacheError):
    """Raised when there's an error acquiring or releasing a cache lock."""

    pass
