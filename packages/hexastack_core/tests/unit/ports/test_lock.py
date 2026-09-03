import pytest

from hexastack_core.adapters.lock import AsyncInMemoryLock, InMemoryLock
from hexastack_core.ports.lock import AsyncLockPort, LockPort


def test_lock_port_context_manager():
    lock: LockPort = InMemoryLock()
    with lock as res:
        assert res is True
        assert lock.locked() is True

    assert lock.locked() is False


@pytest.mark.anyio
async def test_async_lock_port_context_manager():
    lock: AsyncLockPort = AsyncInMemoryLock()
    async with lock as res:
        assert res is True
        assert await lock.locked() is True

    assert await lock.locked() is False
