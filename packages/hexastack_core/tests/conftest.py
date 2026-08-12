from collections.abc import Callable
from typing import Any

import pytest
from hexastack_core.adapters.logging import InMemoryLogger
from hexastack_core.adapters.repository import InMemoryRepository
from hexastack_core.adapters.unit_of_work import InMemoryUnitOfWork


@pytest.fixture
def in_memory_repo_factory() -> Callable[..., InMemoryRepository[Any, Any]]:
    """Fixture providing a factory to create parameterized InMemoryRepository instances."""
    return lambda **kwargs: InMemoryRepository(**kwargs)


@pytest.fixture
def in_memory_repo() -> InMemoryRepository[Any, Any]:
    """Fixture providing a fresh default InMemoryRepository instance."""
    return InMemoryRepository()


@pytest.fixture
def in_memory_logger() -> InMemoryLogger:
    """Fixture providing a fresh default InMemoryLogger instance."""
    return InMemoryLogger()


@pytest.fixture
def in_memory_uow() -> InMemoryUnitOfWork:
    """Fixture providing a fresh default InMemoryUnitOfWork instance."""
    return InMemoryUnitOfWork()
