"""
Base cache backend interface.

This module defines the abstract base class that all cache backends must implement.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseCacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from the cache by key.

        Args:
            key: The key to look up in the cache.
            default: The default value to return if the key is not found.

        Returns:
            The cached value or the default if the key is not found.
        """
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set a value in the cache.

        Args:
            key: The key to set in the cache.
            value: The value to cache.
            timeout: The timeout in seconds (optional).
            nx: If True, set the value only if the key does not exist.
            xx: If True, set the value only if the key already exists.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: The key to delete.

        Returns:
            bool: True if the key was deleted, False if it didn't exist.
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: The key to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the connection to the cache backend."""
        pass

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Fetch a bunch of keys from the cache.

        Args:
            keys: List of keys to fetch.

        Returns:
            A dict mapping keys to values for keys that exist.
        """
        return {key: await self.get(key) for key in keys}

    async def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None) -> None:
        """Set a bunch of values in the cache at once.

        Args:
            data: Dict of key-value pairs to cache.
            timeout: The timeout in seconds (optional).
        """
        for key, value in data.items():
            await self.set(key, value, timeout=timeout)

    async def delete_many(self, keys: List[str]) -> None:
        """Delete a bunch of values from the cache.

        Args:
            keys: List of keys to delete.
        """
        for key in keys:
            await self.delete(key)

    async def get_or_set(self, key: str, default: Any, timeout: Optional[int] = None) -> Any:
        """Fetch a key from the cache, or set it with a default if not present.

        Args:
            key: The key to get or set.
            default: The default value to set if the key doesn't exist.
            timeout: The timeout in seconds (optional).

        Returns:
            The cached value or the default.
        """
        val = await self.get(key, default=None)
        if val is None:
            await self.set(key, default, timeout=timeout)
            return default
        return val

    async def incr(self, key: str, delta: int = 1) -> int:
        """Increment a key's value by delta.

        Args:
            key: The key to increment.
            delta: The amount to increment by (default: 1).

        Returns:
            The new value after incrementing.
        """
        value = await self.get(key, 0)
        if not isinstance(value, (int, float)):
            raise ValueError(f"Value for '{key}' is not a number")
        new_value = value + delta
        await self.set(key, new_value)
        return new_value

    async def decr(self, key: str, delta: int = 1) -> int:
        """Decrement a key's value by delta.

        Args:
            key: The key to decrement.
            delta: The amount to decrement by (default: 1).

        Returns:
            The new value after decrementing.
        """
        return await self.incr(key, -delta)

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get the time-to-live for a key in seconds.

        Args:
            key: The key to check.

        Returns:
            The TTL in seconds, or None if the key does not exist or has no TTL.
        """
        raise NotImplementedError("Subclasses must implement get_ttl()")

    async def set_ttl(self, key: str, timeout: int) -> bool:
        """Set the time-to-live for a key in seconds.

        Args:
            key: The key to set the TTL for.
            timeout: The TTL in seconds.

        Returns:
            bool: True if the TTL was set, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement set_ttl()")

    async def clear(self) -> None:
        """Clear the entire cache."""
        raise NotImplementedError("Subclasses must implement clear()")
