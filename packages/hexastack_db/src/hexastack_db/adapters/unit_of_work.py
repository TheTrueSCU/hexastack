from types import TracebackType
from typing import Self

from hexastack_core.domain.exceptions import UnitOfWorkError
from hexastack_core.ports.unit_of_work import UnitOfWorkPort
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import Session, sessionmaker

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
            try:
                self._session.rollback()
            except SQLAlchemyError:
                pass

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


class AsyncSqlAlchemyUnitOfWork:
    """Asynchronous SQLAlchemy Unit of Work implementation for non-blocking workflows.

    Notes/Architectural Intent:
        Manages async transaction lifecycle over AsyncSession and async_sessionmaker.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        reraise: bool = False,
    ) -> None:
        """Initialize async Unit of Work with async_sessionmaker factory.

        Args:
            session_factory: Configured async_sessionmaker.
            reraise: If True, wraps exceptions in UnitOfWorkError.
        """
        self._session_factory = session_factory
        self._reraise = reraise
        self._session: AsyncSession | None = None

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

    async def rollback(self) -> None:
        """Roll back all pending database changes asynchronously."""
        if self._session is not None:
            try:
                await self._session.rollback()
            except SQLAlchemyError:
                pass

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
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
                if self._reraise:
                    raise UnitOfWorkError() from exc
        finally:
            if self._session is not None:
                await self._session.close()
                self._session = None


__all__ = [
    "AsyncSqlAlchemyUnitOfWork",
    "SqlAlchemyUnitOfWork",
]
