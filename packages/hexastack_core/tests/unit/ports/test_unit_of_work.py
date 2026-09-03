import pytest

from hexastack_core.adapters.unit_of_work import InMemoryUnitOfWork
from hexastack_core.domain import UnitOfWorkError


def test_unit_of_work_exception_reraises_as_unit_of_work_error():
    uow = InMemoryUnitOfWork(reraise=True)

    with pytest.raises(UnitOfWorkError) as exc_info, uow:
        raise ValueError("original error")

    assert uow.committed is False
    assert uow.rolled_back is True
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_unit_of_work_exception_rolls_back_and_propagates():
    uow = InMemoryUnitOfWork(reraise=False)

    with pytest.raises(ValueError, match="test exception"), uow:
        raise ValueError("test exception")

    assert uow.committed is False
    assert uow.rolled_back is True


def test_unit_of_work_success_commits():
    uow = InMemoryUnitOfWork()
    with uow:
        pass

    assert uow.committed is True
    assert uow.rolled_back is False
