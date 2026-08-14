from collections.abc import Callable
from typing import Any

import pytest

from hexastack_core.adapters.ai import InMemoryLlmProvider, InMemoryVectorStore
from hexastack_core.adapters.cache import AsyncInMemoryCache, InMemoryCache
from hexastack_core.adapters.clock import FrozenClock, InMemoryClock
from hexastack_core.adapters.logging import InMemoryLogger
from hexastack_core.adapters.repository import (
    AsyncInMemoryRepository,
    InMemoryRepository,
)
from hexastack_core.adapters.unit_of_work import (
    AsyncInMemoryUnitOfWork,
    InMemoryUnitOfWork,
)


@pytest.fixture
def in_memory_repo_factory() -> Callable[..., InMemoryRepository[Any, Any]]:
    """Fixture providing a factory to create parameterized InMemoryRepository instances."""
    return lambda **kwargs: InMemoryRepository(**kwargs)


@pytest.fixture
def in_memory_repo() -> InMemoryRepository[Any, Any]:
    """Fixture providing a fresh default InMemoryRepository instance."""
    return InMemoryRepository()


@pytest.fixture
def async_in_memory_repo() -> AsyncInMemoryRepository[Any, Any]:
    """Fixture providing a fresh AsyncInMemoryRepository instance."""
    return AsyncInMemoryRepository()


@pytest.fixture
def in_memory_logger() -> InMemoryLogger:
    """Fixture providing a fresh default InMemoryLogger instance."""
    return InMemoryLogger()


@pytest.fixture
def in_memory_uow() -> InMemoryUnitOfWork:
    """Fixture providing a fresh default InMemoryUnitOfWork instance."""
    return InMemoryUnitOfWork()


@pytest.fixture
def async_in_memory_uow() -> AsyncInMemoryUnitOfWork:
    """Fixture providing a fresh AsyncInMemoryUnitOfWork instance."""
    return AsyncInMemoryUnitOfWork()


@pytest.fixture
def in_memory_llm() -> InMemoryLlmProvider:
    """Fixture providing a fresh InMemoryLlmProvider instance."""
    return InMemoryLlmProvider()


@pytest.fixture
def in_memory_vector_store() -> InMemoryVectorStore:
    """Fixture providing a fresh InMemoryVectorStore instance."""
    return InMemoryVectorStore()


@pytest.fixture
def in_memory_cache() -> InMemoryCache:
    """Fixture providing a fresh InMemoryCache instance."""
    return InMemoryCache()


@pytest.fixture
def async_in_memory_cache() -> AsyncInMemoryCache:
    """Fixture providing a fresh AsyncInMemoryCache instance."""
    return AsyncInMemoryCache()


@pytest.fixture
def in_memory_clock() -> InMemoryClock:
    """Fixture providing an InMemoryClock instance."""
    return InMemoryClock()


@pytest.fixture
def frozen_clock() -> FrozenClock:
    """Fixture providing a FrozenClock initialized to current time."""
    return FrozenClock()
