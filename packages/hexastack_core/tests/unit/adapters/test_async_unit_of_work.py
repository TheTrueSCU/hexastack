import pytest
from hexastack_core.adapters.unit_of_work import AsyncInMemoryUnitOfWork
from hexastack_core.domain.exceptions import UnitOfWorkError


@pytest.mark.anyio
async def test_async_in_memory_unit_of_work_lifecycle():
    uow = AsyncInMemoryUnitOfWork()
    assert uow.committed is False
    assert uow.rolled_back is False

    async with uow:
        pass

    assert uow.committed is True
    assert uow.commit_count == 1
    assert uow.rolled_back is False

    # Test rollback on exception
    uow2 = AsyncInMemoryUnitOfWork(reraise=False)
    with pytest.raises(ValueError):
        async with uow2:
            raise ValueError("Test error")

    assert uow2.rolled_back is True
    assert uow2.rollback_count == 1
    assert uow2.committed is False


@pytest.mark.anyio
async def test_async_in_memory_unit_of_work_reraise():
    uow = AsyncInMemoryUnitOfWork(reraise=True)
    with pytest.raises(UnitOfWorkError):
        async with uow:
            raise RuntimeError("Underlying failure")

    assert uow.rolled_back is True
    uow.clear()
    assert uow.rolled_back is False
    assert uow.rollback_count == 0
