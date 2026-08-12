import pytest
from hexastack_core.adapters.unit_of_work import InMemoryUnitOfWork
from hexastack_core.domain import UnitOfWorkError


def test_in_memory_uow_commit():
    uow = InMemoryUnitOfWork()
    assert uow.committed is False
    assert uow.commit_count == 0

    with uow:
        pass

    assert uow.committed is True
    assert uow.commit_count == 1
    assert uow.rolled_back is False


def test_in_memory_uow_rollback_on_exception():
    uow = InMemoryUnitOfWork(reraise=False)

    with pytest.raises(ValueError, match="fail"), uow:
        raise ValueError("fail")

    assert uow.rolled_back is True
    assert uow.rollback_count == 1
    assert uow.committed is False


def test_in_memory_uow_reraise_wraps_in_unit_of_work_error():
    uow = InMemoryUnitOfWork(reraise=True)

    with pytest.raises(UnitOfWorkError), uow:
        raise ValueError("nested failure")

    assert uow.rolled_back is True
    assert uow.rollback_count == 1


def test_in_memory_uow_clear():
    uow = InMemoryUnitOfWork()
    with uow:
        pass

    assert uow.committed is True
    assert uow.commit_count == 1

    uow.clear()
    assert uow.committed is False
    assert uow.commit_count == 0
    assert uow.rolled_back is False
    assert uow.rollback_count == 0
