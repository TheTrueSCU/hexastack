import json
from typing import Any

from hexastack_core.ports.cache import AsyncCachePort, CachePort


def _serialize_value(value: Any) -> str:
    """Serialize a cache value to a JSON string or return clean string/bytes representation.

    Args:
        value: Any Python object to store in the cache.

    Returns:
        JSON-encoded string representing the value.
    """
    if isinstance(value, str):
        return json.dumps({"_hs_type": "str", "v": value})
    if isinstance(value, bytes):
        return json.dumps({"_hs_type": "bytes", "v": value.hex()})
    return json.dumps({"_hs_type": "json", "v": value}, default=str)


def _deserialize_value(raw: str | bytes | None, default: Any = None) -> Any:
    """Deserialize a cached string or bytes back to its Python representation.

    Args:
        raw: Raw value returned from the Redis/Valkey client.
        default: Fallback value returned if raw is None or deserialization fails.

    Returns:
        The deserialized Python object, or default.
    """
    if raw is None:
        return default

    raw_str = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)

    try:
        data = json.loads(raw_str)
        if isinstance(data, dict) and "_hs_type" in data and "v" in data:
            t = data["_hs_type"]
            if t == "str":
                return str(data["v"])
            if t == "bytes":
                return bytes.fromhex(str(data["v"]))
            return data["v"]
        return data
    except Exception:
        return raw_str


class RedisCacheAdapter(CachePort):
    """Synchronous key-value cache adapter backed by Redis or Valkey.

    Notes/Architectural Intent:
        Implements CachePort using a standard synchronous Redis or Valkey client instance
        (e.g. redis.Redis or valkey.Valkey). Supports structured JSON serialization,
        TTL expiration with millisecond/second granularity, and namespace key prefixes.
    """

    def __init__(self, client: Any, key_prefix: str = "") -> None:
        """Initialize RedisCacheAdapter with a synchronous client.

        Args:
            client: Synchronous Redis or Valkey client instance.
            key_prefix: Optional namespace prefix prepended to all cache keys.
        """
        self._client = client
        self._key_prefix = key_prefix

    def _format_key(self, key: str) -> str:
        return f"{self._key_prefix}{key}" if self._key_prefix else key

    def clear(self) -> None:
        """Clear all entries matching the key prefix from the cache."""
        if self._key_prefix:
            pattern = f"{self._key_prefix}*"
            keys = self._client.keys(pattern)
            if keys:
                self._client.delete(*keys)
        else:
            self._client.flushdb()

    def delete(self, key: str) -> bool:
        """Delete a cached key.

        Args:
            key: Cache key to delete.

        Returns:
            True if the key existed and was deleted, False otherwise.
        """
        formatted_key = self._format_key(key)
        res = self._client.delete(formatted_key)
        return bool(res > 0)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a cached value by key.

        Args:
            key: Unique string cache key identifier.
            default: Fallback value returned if the key does not exist or has expired.

        Returns:
            The cached value if present and unexpired, otherwise default.
        """
        formatted_key = self._format_key(key)
        raw = self._client.get(formatted_key)
        return _deserialize_value(raw, default=default)

    def has(self, key: str) -> bool:
        """Check if a key exists in cache and has not expired.

        Args:
            key: Cache key to check.

        Returns:
            True if present and valid, False otherwise.
        """
        formatted_key = self._format_key(key)
        res = self._client.exists(formatted_key)
        return bool(res > 0)

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        """Store a key-value pair in cache with optional TTL expiration.

        Args:
            key: Unique string cache key identifier.
            value: Value to be stored.
            ttl_seconds: Optional time-to-live duration in seconds.
        """
        formatted_key = self._format_key(key)
        serialized = _serialize_value(value)
        if ttl_seconds is not None:
            ttl_ms = int(ttl_seconds * 1000)
            self._client.set(formatted_key, serialized, px=ttl_ms)
        else:
            self._client.set(formatted_key, serialized)


class AsyncRedisCacheAdapter(AsyncCachePort):
    """Asynchronous key-value cache adapter backed by async Redis or Valkey.

    Notes/Architectural Intent:
        Implements AsyncCachePort using an asynchronous Redis or Valkey client instance
        (e.g. redis.asyncio.Redis or valkey.asyncio.Valkey). Handles non-blocking
        network operations and structured serialization.
    """

    def __init__(self, client: Any, key_prefix: str = "") -> None:
        """Initialize AsyncRedisCacheAdapter with an asynchronous client.

        Args:
            client: Asynchronous Redis or Valkey client instance.
            key_prefix: Optional namespace prefix prepended to all cache keys.
        """
        self._client = client
        self._key_prefix = key_prefix

    def _format_key(self, key: str) -> str:
        return f"{self._key_prefix}{key}" if self._key_prefix else key

    async def clear_async(self) -> None:
        """Asynchronously clear all entries matching the key prefix from the cache."""
        if self._key_prefix:
            pattern = f"{self._key_prefix}*"
            keys = await self._client.keys(pattern)
            if keys:
                await self._client.delete(*keys)
        else:
            await self._client.flushdb()

    async def delete_async(self, key: str) -> bool:
        """Asynchronously delete a cached key.

        Args:
            key: Cache key to delete.

        Returns:
            True if the key existed and was deleted, False otherwise.
        """
        formatted_key = self._format_key(key)
        res = await self._client.delete(formatted_key)
        return bool(res > 0)

    async def get_async(self, key: str, default: Any = None) -> Any:
        """Asynchronously retrieve a cached value by key.

        Args:
            key: Unique string cache key identifier.
            default: Fallback value returned if the key does not exist or has expired.

        Returns:
            The cached value if present and unexpired, otherwise default.
        """
        formatted_key = self._format_key(key)
        raw = await self._client.get(formatted_key)
        return _deserialize_value(raw, default=default)

    async def has_async(self, key: str) -> bool:
        """Asynchronously check if a key exists in cache.

        Args:
            key: Cache key to check.

        Returns:
            True if present and valid, False otherwise.
        """
        formatted_key = self._format_key(key)
        res = await self._client.exists(formatted_key)
        return bool(res > 0)

    async def set_async(
        self, key: str, value: Any, ttl_seconds: float | None = None
    ) -> None:
        """Asynchronously store a key-value pair in cache with optional TTL expiration.

        Args:
            key: Unique string cache key identifier.
            value: Value to be stored.
            ttl_seconds: Optional time-to-live duration in seconds.
        """
        formatted_key = self._format_key(key)
        serialized = _serialize_value(value)
        if ttl_seconds is not None:
            ttl_ms = int(ttl_seconds * 1000)
            await self._client.set(formatted_key, serialized, px=ttl_ms)
        else:
            await self._client.set(formatted_key, serialized)


__all__ = [
    "AsyncRedisCacheAdapter",
    "RedisCacheAdapter",
]
