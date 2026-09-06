import pytest

from hexastack_core.adapters.unit_of_work import InMemoryUnitOfWork
from hexastack_core.domain import UnitOfWorkError


@pytest.mark.anyio
async def test_async_in_memory_unit_of_work_lifecycle():
    from hexastack_core.adapters.unit_of_work import AsyncInMemoryUnitOfWork

    uow = AsyncInMemoryUnitOfWork()
    assert uow.committed is False
    assert uow.rolled_back is False
    assert uow.commit_count == 0
    assert uow.rollback_count == 0
    assert uow._reraise is False

    async with uow:
        pass

    assert uow.committed is True
    assert uow.commit_count == 1
    assert uow.rolled_back is False
    assert uow.rollback_count == 0

    # Manual commit call increments count
    await uow.commit_async()
    assert uow.commit_count == 2

    # Manual rollback call increments count
    await uow.rollback_async()
    assert uow.rollback_count == 1

    # Test rollback on exception
    uow2 = AsyncInMemoryUnitOfWork(reraise=False)
    with pytest.raises(ValueError, match="Test error"):
        async with uow2:
            raise ValueError("Test error")

    assert uow2.rolled_back is True
    assert uow2.rollback_count == 1
    assert uow2.committed is False
    assert uow2.commit_count == 0


@pytest.mark.anyio
async def test_async_in_memory_unit_of_work_reraise():
    from hexastack_core.adapters.unit_of_work import AsyncInMemoryUnitOfWork

    uow = AsyncInMemoryUnitOfWork(reraise=True)
    assert uow._reraise is True
    with pytest.raises(UnitOfWorkError):
        async with uow:
            raise RuntimeError("Underlying failure")

    assert uow.rolled_back is True
    assert uow.rollback_count == 1
    assert uow.committed is False
    assert uow.commit_count == 0

    uow.clear()
    assert uow.rolled_back is False
    assert uow.rollback_count == 0
    assert uow.committed is False
    assert uow.commit_count == 0


def test_in_memory_uow_clear():
    uow = InMemoryUnitOfWork()
    assert uow._reraise is False
    with uow:
        pass

    assert uow.committed is True
    assert uow.commit_count == 1

    uow.clear()
    assert uow.committed is False
    assert uow.commit_count == 0
    assert uow.rolled_back is False
    assert uow.rollback_count == 0


def test_in_memory_uow_commit():
    uow = InMemoryUnitOfWork()
    assert uow.committed is False
    assert uow.commit_count == 0

    with uow:
        pass

    assert uow.committed is True
    assert uow.commit_count == 1
    assert uow.rolled_back is False

    # Manual commit increments
    uow.commit()
    assert uow.commit_count == 2


def test_in_memory_uow_reraise_wraps_in_unit_of_work_error():
    uow = InMemoryUnitOfWork(reraise=True)
    assert uow._reraise is True

    with pytest.raises(UnitOfWorkError), uow:
        raise ValueError("nested failure")

    assert uow.rolled_back is True
    assert uow.rollback_count == 1


def test_in_memory_uow_rollback_on_exception():
    uow = InMemoryUnitOfWork(reraise=False)

    with pytest.raises(ValueError, match="fail"), uow:
        raise ValueError("fail")

    assert uow.rolled_back is True
    assert uow.rollback_count == 1
    assert uow.committed is False

    # Manual rollback increments
    uow.rollback()
    assert uow.rollback_count == 2
