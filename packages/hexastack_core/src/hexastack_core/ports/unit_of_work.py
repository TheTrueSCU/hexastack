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

    def __init__(self, reraise: bool = False):
        """Initialize UnitOfWorkPort with reraise option.

        Args:
            reraise: If True, wraps exceptions occurring within context manager into UnitOfWorkError.
                     If False, rolls back and lets original exception propagate.
        """
        self._reraise = reraise

    @abstractmethod
    def commit(self) -> None:
        """Commit all pending transactional changes.

        Returns:
            None.

        Raises:
            UnitOfWorkError: If commit fails.
        """
        ...

    @abstractmethod
    def rollback(self) -> None:
        """Roll back all pending transactional changes.

        Returns:
            None.

        Raises:
            UnitOfWorkError: If rollback fails.
        """
        ...

    def __enter__(self) -> Self:
        """Enter the transactional context manager.

        Returns:
            Self: The UnitOfWorkPort instance.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Exit the transactional context manager, committing on success or rolling back on exception.

        Args:
            exc_type: Exception type if an exception occurred, else None.
            exc: Exception instance if an exception occurred, else None.
            trace: Traceback object if an exception occurred, else None.

        Returns:
            None.

        Raises:
            UnitOfWorkError: If an exception occurred and self._reraise is True.
        """
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

            if self._reraise:
                raise UnitOfWorkError() from exc
