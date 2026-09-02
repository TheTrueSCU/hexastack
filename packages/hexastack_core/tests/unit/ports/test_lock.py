import pytest

from hexastack_core.ports.lock import AsyncLockPort, LockPort


class DummyLock(LockPort):
    def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        return False

    def release(self) -> None:
        pass

    def locked(self) -> bool:
        return False


class DummyAsyncLock(AsyncLockPort):
    async def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        return False

    async def release(self) -> None:
        pass

    async def locked(self) -> bool:
        return False


def test_lock_port_context_manager():
    acquired = False
    released = False

    class MockLock(LockPort):
        def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
            nonlocal acquired
            acquired = True
            return True

        def release(self) -> None:
            nonlocal released
            released = True

        def locked(self) -> bool:
            return acquired and not released

    lock = MockLock()
    with lock as res:
        assert res is True
        assert acquired is True
        assert released is False

    assert released is True


@pytest.mark.anyio
async def test_async_lock_port_context_manager():
    acquired = False
    released = False

    class MockAsyncLock(AsyncLockPort):
        async def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
            nonlocal acquired
            acquired = True
            return True

        async def release(self) -> None:
            nonlocal released
            released = True

        async def locked(self) -> bool:
            return acquired and not released

    lock = MockAsyncLock()
    async with lock as res:
        assert res is True
        assert acquired is True
        assert released is False

    assert released is True
