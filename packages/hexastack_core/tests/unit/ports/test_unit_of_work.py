import inspect

import pytest

from hexastack_core.adapters.unit_of_work import InMemoryUnitOfWork
from hexastack_core.domain import UnitOfWorkError
from hexastack_core.ports.unit_of_work import AsyncUnitOfWorkPort, UnitOfWorkPort


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


def test_unit_of_work_port_is_abstract() -> None:
    """Verify that UnitOfWorkPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(UnitOfWorkPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        UnitOfWorkPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_unit_of_work_port_abstract_methods() -> None:
    """Verify abstract methods on UnitOfWorkPort."""
    expected = {"commit", "rollback"}
    abstracts = UnitOfWorkPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_async_unit_of_work_port_is_abstract() -> None:
    """Verify that AsyncUnitOfWorkPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(AsyncUnitOfWorkPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncUnitOfWorkPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_async_unit_of_work_port_abstract_methods() -> None:
    """Verify abstract methods on AsyncUnitOfWorkPort."""
    expected = {"commit_async", "rollback_async"}
    abstracts = AsyncUnitOfWorkPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
