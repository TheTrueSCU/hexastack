import pytest

from hexastack_core.domain import UnitOfWorkError
from hexastack_core.ports.unit_of_work import UnitOfWorkPort


class MockUnitOfWork(UnitOfWorkPort):
    def __init__(self, reraise: bool = False) -> None:
        super().__init__(reraise=reraise)
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def test_unit_of_work_success_commits():
    uow = MockUnitOfWork()
    with uow:
        pass

    assert uow.committed is True
    assert uow.rolled_back is False


def test_unit_of_work_exception_rolls_back_and_propagates():
    uow = MockUnitOfWork(reraise=False)

    with pytest.raises(ValueError, match="test exception"), uow:
        raise ValueError("test exception")

    assert uow.committed is False
    assert uow.rolled_back is True


def test_unit_of_work_exception_reraises_as_unit_of_work_error():
    uow = MockUnitOfWork(reraise=True)

    with pytest.raises(UnitOfWorkError) as exc_info, uow:
        raise ValueError("original error")

    assert uow.committed is False
    assert uow.rolled_back is True
    assert isinstance(exc_info.value.__cause__, ValueError)
