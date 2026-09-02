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

    # Reentrant acquire increments count
    assert lock.acquire() is True
    assert lock.locked() is True

    # First release leaves it locked because of reentrancy
    lock.release()
    assert lock.locked() is True

    # Final release frees lock
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

    # Reentrant acquire succeeds from the same Task
    assert await lock.acquire(blocking=False) is True
    assert await lock.locked() is True

    # First release decrements count
    await lock.release()
    assert await lock.locked() is True

    # Final release
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


def test_in_memory_lock_reentrancy():
    lock = InMemoryLock()
    assert lock.acquire() is True
    assert lock.acquire() is True
    assert lock.locked() is True

    # Nested context manager
    with lock:
        assert lock.locked() is True

    # Still locked because of the outer acquires
    assert lock.locked() is True

    lock.release()
    assert lock.locked() is True
    lock.release()
    assert lock.locked() is False


@pytest.mark.anyio
async def test_async_in_memory_lock_reentrancy():
    lock = AsyncInMemoryLock()
    assert await lock.acquire() is True
    assert await lock.acquire() is True
    assert await lock.locked() is True

    # Nested async context manager within the same task
    async with lock:
        assert await lock.locked() is True

    # Still locked because outer acquires must be unwound
    assert await lock.locked() is True

    await lock.release()
    assert await lock.locked() is True
    await lock.release()
    assert await lock.locked() is False
