from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from hexastack_core.domain import UnitOfWorkError


class UnitOfWorkPort(ABC):
    """Abstract port interface defining Unit of Work transactional boundaries.

    Notes/Architectural Intent:
        Manages atomic transaction commit/rollback behavior using Python context managers.
        UnitOfWorkError is defined in hexastack_core.domain so it can be caught at domain
        layer without importing port infrastructure.
    """

    def __init__(self, reraise: bool = False) -> None:
        """Initialize UnitOfWorkPort with reraise option.

        Args:
            reraise: If True, wraps exceptions occurring within context manager into UnitOfWorkError.
                     If False, rolls back and lets original exception propagate.
        """
        self._reraise = reraise

    def __enter__(self) -> Self:
        """Enter the transactional context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Exit the transactional context manager, committing on success or rolling back on exception."""
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

            if self._reraise:
                raise UnitOfWorkError from exc

    @abstractmethod
    def commit(self) -> None:
        """Commit all pending transactional changes."""

    @abstractmethod
    def rollback(self) -> None:
        """Roll back all pending transactional changes."""


class AsyncUnitOfWorkPort(ABC):
    """Abstract port interface defining asynchronous Unit of Work transactional boundaries."""

    def __init__(self, reraise: bool = False) -> None:
        self._reraise = reraise

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        if exc_type is None:
            await self.commit_async()
        else:
            await self.rollback_async()

            if self._reraise:
                raise UnitOfWorkError from exc

    @abstractmethod
    async def commit_async(self) -> None:
        """Asynchronously commit all pending transactional changes."""

    @abstractmethod
    async def rollback_async(self) -> None:
        """Asynchronously roll back all pending transactional changes."""


__all__ = [
    "AsyncUnitOfWorkPort",
    "UnitOfWorkPort",
]
