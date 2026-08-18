from abc import ABC, abstractmethod
from typing import Any


class CachePort(ABC):
    """Abstract interface defining synchronous key-value caching operations.

    Notes/Architectural Intent:
        Decouples application services and query caching middlewares from specific
        cache stores (e.g. In-Memory dict, Redis, Memcached).
    """

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries from the cache."""
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a cached key.

        Args:
            key: Cache key to delete.

        Returns:
            True if the key existed and was deleted, False otherwise.
        """
        ...

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a cached value by key.

        Args:
            key: Unique string cache key identifier.
            default: Fallback value returned if the key does not exist or has expired.

        Returns:
            The cached value if present and unexpired, otherwise default.
        """
        ...

    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if a key exists in cache and has not expired.

        Args:
            key: Cache key to check.

        Returns:
            True if present and valid, False otherwise.
        """
        ...

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        """Store a key-value pair in cache with optional TTL expiration.

        Args:
            key: Unique string cache key identifier.
            value: Value to be stored.
            ttl_seconds: Optional time-to-live duration in seconds.
        """
        ...


class AsyncCachePort(ABC):
    """Abstract interface defining asynchronous key-value caching operations."""

    @abstractmethod
    async def clear_async(self) -> None:
        """Asynchronously clear all entries from the cache."""
        ...

    @abstractmethod
    async def delete_async(self, key: str) -> bool:
        """Asynchronously delete a cached key."""
        ...

    @abstractmethod
    async def get_async(self, key: str, default: Any = None) -> Any:
        """Asynchronously retrieve a cached value by key."""
        ...

    @abstractmethod
    async def has_async(self, key: str) -> bool:
        """Asynchronously check if a key exists in cache."""
        ...

    @abstractmethod
    async def set_async(
        self, key: str, value: Any, ttl_seconds: float | None = None
    ) -> None:
        """Asynchronously store a key-value pair in cache."""
        ...


__all__ = [
    "AsyncCachePort",
    "CachePort",
]
