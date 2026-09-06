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
        mock_redis, key="lock:order:2", ttl_seconds=5.0, retry_interval_seconds=0.005
    )

    # Non-blocking acquire returns False when unavailable and verifies arguments passed to set
    res_non_blocking = lock.acquire(blocking=False)
    assert res_non_blocking is False
    assert lock._token is None
    mock_redis.set.assert_called_with(
        "lock:order:2", mock_redis.set.call_args[0][1], nx=True, px=5000
    )

    # Blocking with timeout 0 returns False immediately on deadline
    res_timeout_0 = lock.acquire(blocking=True, timeout=0.0)
    assert res_timeout_0 is False

    # Blocking with timeout > 0 returns False on deadline
    res_timeout = lock.acquire(blocking=True, timeout=0.01)
    assert res_timeout is False

    # Acquire succeeds after initial failure
    mock_redis.set.side_effect = [False, True]
    res_eventual = lock.acquire(blocking=True, timeout=0.05)
    assert res_eventual is True
    assert lock._token is not None
    mock_redis.set.side_effect = None


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
        mock_redis, key="lock:async:2", ttl_seconds=5.0, retry_interval_seconds=0.005
    )
    res_non_blocking = await lock.acquire(blocking=False)
    assert res_non_blocking is False
    assert lock._token is None
    mock_redis.set.assert_called_with(
        "lock:async:2", mock_redis.set.call_args[0][1], nx=True, px=5000
    )

    res_timeout_0 = await lock.acquire(blocking=True, timeout=0.0)
    assert res_timeout_0 is False

    res_timeout = await lock.acquire(blocking=True, timeout=0.01)
    assert res_timeout is False

    # Eventual acquire succeeds
    mock_redis.set = AsyncMock(side_effect=[False, True])
    res_eventual = await lock.acquire(blocking=True, timeout=0.05)
    assert res_eventual is True
    assert lock._token is not None


@pytest.mark.anyio
async def test_async_redis_lock_adapter_release_lost_lock():
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.eval = AsyncMock(return_value=0)

    lock = AsyncRedisLockAdapter(mock_redis, key="lock:async:3", ttl_seconds=5.0)
    assert await lock.acquire() is True

    with pytest.raises(LockError, match="Lock was lost or expired"):
        await lock.release()
