import inspect

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


def test_lock_port_is_abstract() -> None:
    """Verify that LockPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(LockPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        LockPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_lock_port_abstract_methods() -> None:
    """Verify abstract methods on LockPort."""
    expected = {"acquire", "locked", "release"}
    abstracts = LockPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_async_lock_port_is_abstract() -> None:
    """Verify that AsyncLockPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(AsyncLockPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncLockPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_async_lock_port_abstract_methods() -> None:
    """Verify abstract methods on AsyncLockPort."""
    expected = {"acquire", "locked", "release"}
    abstracts = AsyncLockPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
