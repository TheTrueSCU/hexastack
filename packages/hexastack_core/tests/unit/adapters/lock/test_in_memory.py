import pytest

from hexastack_core.adapters.lock.in_memory import (
    AsyncInMemoryLock,
    InMemoryLock,
)
from hexastack_core.domain.exceptions import LockError


def test_in_memory_lock_basic_flow():
    lock = InMemoryLock()
    assert lock.locked() is False

    # Acquire
    assert lock.acquire() is True
    assert lock.locked() is True

    # Reentrant / secondary acquire
    assert lock.acquire() is True

    # Release
    lock.release()
    assert lock.locked() is False

    # Cannot release when not held
    with pytest.raises(LockError):
        lock.release()


def test_in_memory_lock_context_manager():
    lock = InMemoryLock()
    with lock:
        assert lock.locked() is True

    assert lock.locked() is False


@pytest.mark.anyio
async def test_async_in_memory_lock_basic_flow():
    lock = AsyncInMemoryLock()
    assert await lock.locked() is False

    assert await lock.acquire() is True
    assert await lock.locked() is True

    # Non-blocking acquire fails when locked
    assert await lock.acquire(blocking=False) is False

    # Timeout acquire fails when locked
    assert await lock.acquire(blocking=True, timeout=0.01) is False

    await lock.release()
    assert await lock.locked() is False

    # Cannot release when unlocked
    with pytest.raises(LockError):
        await lock.release()


@pytest.mark.anyio
async def test_async_in_memory_lock_context_manager():
    lock = AsyncInMemoryLock()
    async with lock:
        assert await lock.locked() is True

    assert await lock.locked() is False
