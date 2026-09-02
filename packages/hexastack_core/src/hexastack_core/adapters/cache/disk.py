import tempfile
from pathlib import Path
from typing import Any

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_core.ports.cache import AsyncCachePort, CachePort


class DiskCacheAdapter(CachePort):
    """Persistent L2 query and key-value cache adapter backed by diskcache (SQLite + mmap).

    Notes/Architectural Intent:
        Implements CachePort using diskcache.Cache on local filesystem storage.
        Enables multi-process cache sharing, persistent caching across service restarts,
        and offline CLI response caching without Redis or network dependencies.
    """

    def __init__(
        self,
        directory: str | Path | None = None,
        size_limit: int = 1_073_741_824,  # 1GB default
    ) -> None:
        """Initialize DiskCacheAdapter.

        Args:
            directory: Filesystem path to cache database directory. If None, creates a tempdir.
            size_limit: Maximum cache size in bytes before eviction.

        Raises:
            MissingDependencyError: If `diskcache` is not installed.
        """
        try:
            import diskcache
        except ImportError as e:
            raise MissingDependencyError(
                "The 'diskcache' package is required to use DiskCacheAdapter. "
                "Install it with: pip install hexastack-core[diskcache]"
            ) from e

        self._directory = (
            Path(directory)
            if directory
            else Path(tempfile.mkdtemp(prefix="hexastack_cache_"))
        )
        self._cache: Any = diskcache.Cache(str(self._directory), size_limit=size_limit)

    def clear(self) -> None:
        """Clear all entries from the disk cache."""
        self._cache.clear()

    def delete(self, key: str) -> bool:
        """Delete a key from disk cache.

        Args:
            key: Cache key to remove.

        Returns:
            True if key was deleted, False if not present.
        """
        return bool(self._cache.delete(key))

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a cached value by key.

        Args:
            key: Cache key identifier.
            default: Default fallback if missing or expired.

        Returns:
            Cached value or default.
        """
        return self._cache.get(key, default=default)

    def has(self, key: str) -> bool:
        """Check if a key is present and unexpired.

        Args:
            key: Cache key identifier.

        Returns:
            True if present, False otherwise.
        """
        return key in self._cache

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        """Store a key-value pair with optional TTL expiration in seconds.

        Args:
            key: Cache key identifier.
            value: Value object to persist.
            ttl_seconds: Time to live in seconds.
        """
        self._cache.set(key, value, expire=ttl_seconds)

    def close(self) -> None:
        """Close underlying SQLite database handles."""
        self._cache.close()


class AsyncDiskCacheAdapter(AsyncCachePort):
    """Asynchronous persistent L2 query and key-value cache adapter backed by diskcache.

    Notes/Architectural Intent:
        Async counterpart to DiskCacheAdapter, offloading blocking disk I/O to the threadpool
        via `asyncio.to_thread`.
    """

    def __init__(
        self,
        directory: str | Path | None = None,
        size_limit: int = 1_073_741_824,
    ) -> None:
        """Initialize AsyncDiskCacheAdapter.

        Args:
            directory: Directory path for diskcache.
            size_limit: Maximum cache size in bytes.
        """
        self._sync_adapter = DiskCacheAdapter(
            directory=directory, size_limit=size_limit
        )

    async def clear_async(self) -> None:
        """Clear all entries asynchronously."""
        import asyncio

        await asyncio.to_thread(self._sync_adapter.clear)

    async def delete_async(self, key: str) -> bool:
        """Delete a key asynchronously."""
        import asyncio

        return await asyncio.to_thread(self._sync_adapter.delete, key)

    async def get_async(self, key: str, default: Any = None) -> Any:
        """Retrieve a cached value asynchronously."""
        import asyncio

        return await asyncio.to_thread(self._sync_adapter.get, key, default)

    async def has_async(self, key: str) -> bool:
        """Check if a key exists asynchronously."""
        import asyncio

        return await asyncio.to_thread(self._sync_adapter.has, key)

    async def set_async(
        self, key: str, value: Any, ttl_seconds: float | None = None
    ) -> None:
        """Store a key-value pair asynchronously."""
        import asyncio

        await asyncio.to_thread(self._sync_adapter.set, key, value, ttl_seconds)

    async def close_async(self) -> None:
        """Close cache handles asynchronously."""
        import asyncio

        await asyncio.to_thread(self._sync_adapter.close)


__all__ = [
    "AsyncDiskCacheAdapter",
    "DiskCacheAdapter",
]
