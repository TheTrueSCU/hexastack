import contextlib
from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import Session, sessionmaker

from hexastack_core.domain.exceptions import UnitOfWorkError
from hexastack_core.ports.unit_of_work import (
    AsyncUnitOfWorkPort,
    UnitOfWorkPort,
)
from hexastack_db.domain.exceptions import DatabaseError


class SqlAlchemyUnitOfWork(UnitOfWorkPort):
    """SQLAlchemy implementation of UnitOfWorkPort.

    Notes/Architectural Intent:
        Manages transactional boundaries using SQLAlchemy Session lifecycle,
        automatically committing clean execution blocks and rolling back on failure.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        reraise: bool = False,
    ) -> None:
        """Initialize Unit of Work with sessionmaker factory.

        Args:
            session_factory: Configured SQLAlchemy sessionmaker.
            reraise: If True, wraps exceptions in UnitOfWorkError.
        """
        super().__init__(reraise=reraise)
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> Self:
        """Enter transactional scope and acquire fresh database Session."""
        self._session = self._session_factory()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Exit transactional scope, commit or rollback, and close session."""
        try:
            super().__exit__(exc_type, exc, trace)
        finally:
            if self._session is not None:
                self._session.close()
                self._session = None

    def commit(self) -> None:
        """Commit all pending database changes in active session.

        Raises:
            UnitOfWorkError: If committing transaction fails.
        """
        if self._session is not None:
            try:
                self._session.commit()
            except SQLAlchemyError as exc:
                self._session.rollback()
                raise UnitOfWorkError() from exc

    def rollback(self) -> None:
        """Roll back all pending database changes in active session."""
        if self._session is not None:
            with contextlib.suppress(SQLAlchemyError):
                self._session.rollback()

    @property
    def session(self) -> Session:
        """Active SQLAlchemy Session in current transactional scope.

        Returns:
            Current Session.

        Raises:
            DatabaseError: If accessed outside of transactional context manager.
        """
        if self._session is None:
            raise DatabaseError(
                "UnitOfWork session is not active. Use within 'with uow:' context."
            )
        return self._session


class AsyncSqlAlchemyUnitOfWork(AsyncUnitOfWorkPort):
    """Asynchronous SQLAlchemy Unit of Work implementation.

    Notes/Architectural Intent:
        Wraps an asynchronous session and guarantees rollback on error
        and session closure when exiting async context blocks.
    """

    def __init__(
        self,
        session_factory: (
            async_sessionmaker[AsyncSession] | Callable[[], AsyncSession]
        ),
        reraise: bool = False,
    ) -> None:
        super().__init__(reraise=reraise)
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        """Enter asynchronous transactional scope and acquire fresh AsyncSession."""
        self._session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Exit asynchronous transactional scope, commit or rollback, and close session."""
        try:
            await super().__aexit__(exc_type, exc, trace)
        finally:
            if self._session is not None:
                await self._session.close()
                self._session = None

    async def commit(self) -> None:
        """Commit all pending database changes asynchronously.

        Raises:
            UnitOfWorkError: If committing transaction fails.
        """
        if self._session is not None:
            try:
                await self._session.commit()
            except SQLAlchemyError as exc:
                await self._session.rollback()
                raise UnitOfWorkError() from exc

    async def commit_async(self) -> None:
        """Asynchronously commit all pending transactional changes."""
        await self.commit()

    async def rollback(self) -> None:
        """Roll back all pending database changes asynchronously."""
        if self._session is not None:
            with contextlib.suppress(SQLAlchemyError):
                await self._session.rollback()

    async def rollback_async(self) -> None:
        """Asynchronously roll back all pending transactional changes."""
        await self.rollback()

    @property
    def session(self) -> AsyncSession:
        """Active AsyncSession in current transactional scope.

        Returns:
            Current AsyncSession.

        Raises:
            DatabaseError: If accessed outside of async transactional context.
        """
        if self._session is None:
            raise DatabaseError(
                "AsyncUnitOfWork session is not active. Use within 'async with uow:' context."
            )
        return self._session


__all__ = [
    "AsyncSqlAlchemyUnitOfWork",
    "SqlAlchemyUnitOfWork",
]
