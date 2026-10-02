import time
from typing import Any

from hexastack_core.ports.cache import AsyncCachePort, CachePort
from hexastack_core.ports.clock import ClockPort


class InMemoryCache(CachePort):
    """In-memory dictionary cache adapter with TTL expiration support.

    Notes/Architectural Intent:
        Implements CachePort for local development, caching middleware tests,
        and unit testing without requiring Redis. Accepts an optional ClockPort
        for deterministic time testing.
    """

    def __init__(self, clock: ClockPort | None = None) -> None:
        """Initialize empty in-memory cache.

        Args:
            clock: Optional ClockPort instance for time measurement.
        """
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._clock = clock

    def _now(self) -> float:
        return self._clock.timestamp() if self._clock else time.time()

    def clear(self) -> None:
        """Clear all keys from the cache."""
        self._store.clear()

    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        return self._store.pop(key, None) is not None

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a cached value if present and not expired."""
        if key not in self._store:
            return default
        val, expiry = self._store[key]
        if expiry is not None and self._now() > expiry:
            del self._store[key]
            return default
        return val

    def has(self, key: str) -> bool:
        """Check if a key exists and has not expired."""
        if key not in self._store:
            return False
        _, expiry = self._store[key]
        if expiry is not None and self._now() > expiry:
            del self._store[key]
            return False
        return True

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        """Store a cached value with optional TTL expiration."""
        expiry = self._now() + ttl_seconds if ttl_seconds is not None else None
        self._store[key] = (value, expiry)


class AsyncInMemoryCache(AsyncCachePort):
    """Asynchronous in-memory cache adapter."""

    def __init__(self, clock: ClockPort | None = None) -> None:
        self._sync_cache = InMemoryCache(clock=clock)

    async def clear_async(self) -> None:
        self._sync_cache.clear()

    async def delete_async(self, key: str) -> bool:
        return self._sync_cache.delete(key)

    async def get_async(self, key: str, default: Any = None) -> Any:
        return self._sync_cache.get(key, default)

    async def has_async(self, key: str) -> bool:
        return self._sync_cache.has(key)

    async def set_async(
        self, key: str, value: Any, ttl_seconds: float | None = None
    ) -> None:
        self._sync_cache.set(key, value, ttl_seconds)


__all__ = [
    "AsyncInMemoryCache",
    "InMemoryCache",
]
