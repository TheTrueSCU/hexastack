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


def test_in_memory_lock_multithreaded_contention():
    import threading

    lock = InMemoryLock()
    acquired_by_thread1 = threading.Event()
    release_thread1 = threading.Event()
    thread2_result: list[bool] = []
    thread2_error: list[Exception] = []

    def worker1():
        if lock.acquire():
            acquired_by_thread1.set()
            release_thread1.wait(timeout=2.0)
            lock.release()

    def worker2():
        acquired_by_thread1.wait(timeout=2.0)
        # Cannot acquire non-blocking when held
        res = lock.acquire(blocking=False)
        thread2_result.append(res)
        # Cannot release lock held by another thread
        try:
            lock.release()
        except LockError as exc:
            thread2_error.append(exc)

    t1 = threading.Thread(target=worker1)
    t2 = threading.Thread(target=worker2)
    t1.start()
    t2.start()

    t2.join(timeout=2.0)
    release_thread1.set()
    t1.join(timeout=2.0)

    assert thread2_result == [False]
    assert len(thread2_error) == 1
    assert (
        "Cannot release an unacquired lock or a lock owned by another thread."
        in str(thread2_error[0])
    )
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


@pytest.mark.anyio
async def test_async_in_memory_lock_multitask_contention():
    import asyncio

    lock = AsyncInMemoryLock()
    acquired_by_task1 = asyncio.Event()
    release_task1 = asyncio.Event()
    task2_results: dict[str, bool] = {}
    task2_errors: list[Exception] = []

    async def task1_coro():
        acq = await lock.acquire(blocking=True, timeout=-1.0)
        assert acq is True
        acquired_by_task1.set()
        await release_task1.wait()
        await lock.release()

    async def task2_coro():
        await acquired_by_task1.wait()
        # Non-blocking attempt fails
        task2_results["non_blocking"] = await lock.acquire(blocking=False)
        # Timed attempt fails
        task2_results["timed"] = await lock.acquire(blocking=True, timeout=0.01)
        # Cannot release lock held by task1
        try:
            await lock.release()
        except LockError as exc:
            task2_errors.append(exc)

    t1 = asyncio.create_task(task1_coro())
    t2 = asyncio.create_task(task2_coro())

    _ = await t2
    release_task1.set()
    _ = await t1

    assert task2_results["non_blocking"] is False
    assert task2_results["timed"] is False
    assert len(task2_errors) == 1
    assert "Cannot release an unacquired lock or a lock owned by another task." in str(
        task2_errors[0]
    )
    assert await lock.locked() is False


@pytest.mark.anyio
async def test_async_in_memory_lock_timeout_success():
    lock = AsyncInMemoryLock()
    # Timed acquire when free succeeds
    res = await lock.acquire(blocking=True, timeout=1.0)
    assert res is True
    assert await lock.locked() is True
    await lock.release()
    assert await lock.locked() is False
