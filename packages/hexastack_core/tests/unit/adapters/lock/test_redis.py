from unittest.mock import AsyncMock, MagicMock

import pytest

from hexastack_core.adapters.lock.redis import (
    AsyncRedisLockAdapter,
    RedisLockAdapter,
)
from hexastack_core.domain.exceptions import LockError


def test_redis_lock_adapter_sync_flow():
    mock_redis = MagicMock()
    mock_redis.set.return_value = True
    mock_redis.eval.return_value = 1
    mock_redis.exists.return_value = 1

    lock = RedisLockAdapter(mock_redis, key="lock:order:1", ttl_seconds=5.0)

    # Acquire
    assert lock.acquire() is True
    assert lock.locked() is True

    # Release
    lock.release()

    # Verify calls
    mock_redis.set.assert_called_once()
    mock_redis.eval.assert_called_once()


def test_redis_lock_adapter_acquire_failure_and_non_blocking():
    mock_redis = MagicMock()
    mock_redis.set.return_value = False

    lock = RedisLockAdapter(mock_redis, key="lock:order:2", ttl_seconds=5.0)

    # Non-blocking acquire returns False when unavailable
    assert lock.acquire(blocking=False) is False


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
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.eval = AsyncMock(return_value=1)
    mock_redis.exists = AsyncMock(return_value=1)

    lock = AsyncRedisLockAdapter(mock_redis, key="lock:async:1", ttl_seconds=5.0)

    assert await lock.acquire() is True
    assert await lock.locked() is True

    await lock.release()

    mock_redis.set.assert_called_once()
    mock_redis.eval.assert_called_once()


@pytest.mark.anyio
async def test_async_redis_lock_adapter_acquire_failure():
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=False)

    lock = AsyncRedisLockAdapter(mock_redis, key="lock:async:2", ttl_seconds=5.0)
    assert await lock.acquire(blocking=False) is False


@pytest.mark.anyio
async def test_async_redis_lock_adapter_release_lost_lock():
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.eval = AsyncMock(return_value=0)

    lock = AsyncRedisLockAdapter(mock_redis, key="lock:async:3", ttl_seconds=5.0)
    assert await lock.acquire() is True

    with pytest.raises(LockError, match="Lock was lost or expired"):
        await lock.release()
