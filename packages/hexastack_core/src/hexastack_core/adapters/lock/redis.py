import time
import uuid
from typing import Any

from hexastack_core.domain.exceptions import LockError
from hexastack_core.ports.lock import AsyncLockPort, LockPort

_RELEASE_LUA_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class RedisLockAdapter(LockPort):
    """Distributed mutual exclusion lock adapter backed by Redis or Valkey.

    Notes/Architectural Intent:
        Implements distributed mutual exclusion using atomic SET NX PX with unique token
        identification and Lua script release validation to prevent accidental lock release
        by expired or stale owners.
    """

    def __init__(
        self,
        client: Any,
        key: str,
        ttl_seconds: float = 30.0,
        retry_interval_seconds: float = 0.1,
    ) -> None:
        """Initialize RedisLockAdapter.

        Args:
            client: Synchronous Redis/Valkey client instance (redis.Redis or valkey.Valkey).
            key: Distributed lock resource key in Redis.
            ttl_seconds: Lock auto-release expiration time in seconds (safety against crashes).
            retry_interval_seconds: Sleep duration between polling attempts during blocking acquire.
        """
        self._client = client
        self._key = key
        self._ttl_seconds = ttl_seconds
        self._retry_interval = retry_interval_seconds
        self._token: str | None = None

    def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the distributed lock in Redis.

        Args:
            blocking: Whether to wait for lock availability.
            timeout: Maximum seconds to wait if blocking. Negative numbers block infinitely.

        Returns:
            True if acquired, False otherwise.
        """
        token = str(uuid.uuid4())
        px_millis = max(1, int(self._ttl_seconds * 1000))
        deadline = (time.monotonic() + timeout) if timeout >= 0 else None

        while True:
            # Atomic acquire: SET key token NX PX px_millis
            acquired = bool(self._client.set(self._key, token, nx=True, px=px_millis))
            if acquired:
                self._token = token
                return True

            if not blocking:
                return False

            if deadline is not None and time.monotonic() >= deadline:
                return False

            time.sleep(self._retry_interval)

    def release(self) -> None:
        """Release the acquired distributed lock atomically via Lua script.

        Raises:
            LockError: If the lock was not held or ownership was lost.
        """
        if self._token is None:
            raise LockError("Cannot release an unacquired lock.")

        token = self._token
        self._token = None

        try:
            res = self._client.eval(_RELEASE_LUA_SCRIPT, 1, self._key, token)
            if res != 1:
                raise LockError("Lock was lost or expired before release.")
        except Exception as e:
            if isinstance(e, LockError):
                raise
            raise LockError(f"Failed to release Redis lock: {e}") from e

    def locked(self) -> bool:
        """Check if the resource key is currently locked in Redis.

        Returns:
            True if lock key exists in Redis, False otherwise.
        """
        try:
            return bool(self._client.exists(self._key))
        except Exception:
            return False


class AsyncRedisLockAdapter(AsyncLockPort):
    """Asynchronous distributed mutual exclusion lock adapter backed by Redis or Valkey.

    Notes/Architectural Intent:
        Coroutine-safe async counterpart to RedisLockAdapter using async Redis/Valkey clients
        (e.g., redis.asyncio.Redis).
    """

    def __init__(
        self,
        client: Any,
        key: str,
        ttl_seconds: float = 30.0,
        retry_interval_seconds: float = 0.1,
    ) -> None:
        """Initialize AsyncRedisLockAdapter.

        Args:
            client: Asynchronous Redis client instance (redis.asyncio.Redis).
            key: Distributed lock resource key in Redis.
            ttl_seconds: Lock auto-release expiration time in seconds.
            retry_interval_seconds: Sleep duration between polling attempts during blocking acquire.
        """
        self._client = client
        self._key = key
        self._ttl_seconds = ttl_seconds
        self._retry_interval = retry_interval_seconds
        self._token: str | None = None

    async def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the distributed lock asynchronously in Redis.

        Args:
            blocking: Whether to wait for lock availability.
            timeout: Maximum seconds to wait if blocking.

        Returns:
            True if acquired, False otherwise.
        """
        import asyncio

        token = str(uuid.uuid4())
        px_millis = max(1, int(self._ttl_seconds * 1000))
        deadline = (time.monotonic() + timeout) if timeout >= 0 else None

        while True:
            acquired = bool(
                await self._client.set(self._key, token, nx=True, px=px_millis)
            )
            if acquired:
                self._token = token
                return True

            if not blocking:
                return False

            if deadline is not None and time.monotonic() >= deadline:
                return False

            await asyncio.sleep(self._retry_interval)

    async def release(self) -> None:
        """Release the acquired distributed lock asynchronously via Lua script.

        Raises:
            LockError: If the lock was not held or ownership was lost.
        """
        if self._token is None:
            raise LockError("Cannot release an unacquired lock.")

        token = self._token
        self._token = None

        try:
            res = await self._client.eval(_RELEASE_LUA_SCRIPT, 1, self._key, token)
            if res != 1:
                raise LockError("Lock was lost or expired before release.")
        except Exception as e:
            if isinstance(e, LockError):
                raise
            raise LockError(f"Failed to release Redis lock: {e}") from e

    async def locked(self) -> bool:
        """Check if the resource key is currently locked in Redis asynchronously.

        Returns:
            True if lock key exists in Redis, False otherwise.
        """
        try:
            return bool(await self._client.exists(self._key))
        except Exception:
            return False


__all__ = [
    "AsyncRedisLockAdapter",
    "RedisLockAdapter",
]
