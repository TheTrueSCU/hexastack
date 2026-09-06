from unittest.mock import AsyncMock, MagicMock

import pytest

from hexastack_core.adapters.lock.redis import (
    AsyncRedisLockAdapter,
    RedisLockAdapter,
)
from hexastack_core.domain.exceptions import LockError


def test_redis_lock_adapter_sync_flow():
    mock_redis = MagicMock()
    # Test default initialization
    default_lock = RedisLockAdapter(mock_redis, key="lock:default")
    assert default_lock._ttl_seconds == 30.0
    assert default_lock._retry_interval == 0.1
    assert default_lock._token is None

    mock_redis.set.return_value = True
    mock_redis.eval.return_value = 1
    mock_redis.exists.return_value = 1

    lock = RedisLockAdapter(mock_redis, key="lock:order:1", ttl_seconds=5.0)

    # Context manager test
    with lock:
        assert lock.locked() is True

    # Error handling on locked
    mock_redis.exists.side_effect = RuntimeError("Redis down")
    assert lock.locked() is False
    mock_redis.exists.side_effect = None

    # Error handling on release eval exception
    lock._token = "some-token"
    mock_redis.eval.side_effect = RuntimeError("Network partition")
    with pytest.raises(LockError, match="Failed to release Redis lock"):
        lock.release()
    mock_redis.eval.side_effect = None


def test_redis_lock_adapter_acquire_failure_and_non_blocking():
    mock_redis = MagicMock()
    mock_redis.set.return_value = False

    lock = RedisLockAdapter(
        mock_redis, key="lock:order:2", ttl_seconds=5.0, retry_interval_seconds=0.01
    )

    # Non-blocking acquire returns False when unavailable
    assert lock.acquire(blocking=False) is False

    # Blocking with timeout returns False on deadline
    assert lock.acquire(blocking=True, timeout=0.03) is False


def test_redis_lock_adapter_release_lost_lock():
    mock_redis = MagicMock()
    mock_redis.set.return_value = True
    # Lua script returns 0 indicating key did not match token or expired
    mock_redis.eval.return_value = 0

    lock = RedisLockAdapter(mock_redis, key="lock:order:3", ttl_seconds=5.0)
    assert lock.acquire() is True

    with pytest.raises(LockError, match="Lock was lost or expired"):
        lock.release()


def test_redis_lock_adapter_release_unacquired():
    mock_redis = MagicMock()
    lock = RedisLockAdapter(mock_redis, key="lock:order:4")

    with pytest.raises(LockError, match="Cannot release an unacquired lock"):
        lock.release()


@pytest.mark.anyio
async def test_async_redis_lock_adapter_flow():
    mock_redis = MagicMock()
    # Test default initialization
    default_async_lock = AsyncRedisLockAdapter(mock_redis, key="lock:async_default")
    assert default_async_lock._ttl_seconds == 30.0
    assert default_async_lock._retry_interval == 0.1
    assert default_async_lock._token is None

    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.eval = AsyncMock(return_value=1)
    mock_redis.exists = AsyncMock(return_value=1)

    lock = AsyncRedisLockAdapter(mock_redis, key="lock:async:1", ttl_seconds=5.0)

    # Async Context Manager
    async with lock:
        assert await lock.locked() is True

    # Error handling on locked
    mock_redis.exists = AsyncMock(side_effect=RuntimeError("Redis down"))
    assert await lock.locked() is False
    mock_redis.exists = AsyncMock(return_value=1)

    # Error handling on unacquired release
    with pytest.raises(LockError, match="Cannot release an unacquired lock"):
        await lock.release()

    # Error handling on release eval exception
    lock._token = "some-async-token"
    mock_redis.eval = AsyncMock(side_effect=RuntimeError("Network partition"))
    with pytest.raises(LockError, match="Failed to release Redis lock"):
        await lock.release()
    mock_redis.eval = AsyncMock(return_value=1)


@pytest.mark.anyio
async def test_async_redis_lock_adapter_acquire_failure():
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=False)

    lock = AsyncRedisLockAdapter(
        mock_redis, key="lock:async:2", ttl_seconds=5.0, retry_interval_seconds=0.01
    )
    assert await lock.acquire(blocking=False) is False
    assert await lock.acquire(blocking=True, timeout=0.03) is False


@pytest.mark.anyio
async def test_async_redis_lock_adapter_release_lost_lock():
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.eval = AsyncMock(return_value=0)

    lock = AsyncRedisLockAdapter(mock_redis, key="lock:async:3", ttl_seconds=5.0)
    assert await lock.acquire() is True

    with pytest.raises(LockError, match="Lock was lost or expired"):
        await lock.release()
