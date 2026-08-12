"""SQLAlchemy session-per-request middleware for FastAPI.

Decoupling strategy:
    This module depends only on SQLAlchemy (already a transitive dep via hexastack-db)
    and Starlette (already a direct dep via FastAPI). It never imports from hexastack-db.
    Session factories are resolved from the DI container by SQLAlchemy type at runtime,
    so the two packages remain fully independent — the DI container is the only coupling.

Usage:
    # In your app setup (after bootstrapping both DatabaseBootstrapper + FastApiBootstrapper):
    from hexastack_fastapi.adapters.db_session import (
        DbSessionMiddleware,
        AsyncDbSessionMiddleware,
    )

    # Sync engine:
    app.add_middleware(DbSessionMiddleware, session_factory=session_factory)

    # Async engine:
    app.add_middleware(AsyncDbSessionMiddleware, session_factory=async_session_factory)

    # In a handler or dependency:
    def my_endpoint(request: Request):
        session = request.state.db_session   # Session | AsyncSession
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class DbSessionMiddleware(BaseHTTPMiddleware):
    """Synchronous SQLAlchemy session-per-request Starlette middleware.

    Notes/Architectural Intent:
        Creates a new Session for every HTTP request and exposes it as
        request.state.db_session. The session is always closed in the
        finally block regardless of response outcome. No commit is issued
        automatically — handlers own transaction boundaries via UnitOfWork.
    """

    def __init__(
        self,
        app: ASGIApp,
        session_factory: Callable[[], Any],
    ) -> None:
        """Initialise with a synchronous sessionmaker callable.

        Args:
            app: The ASGI application to wrap.
            session_factory: A callable returning a SQLAlchemy Session
                (e.g. the sessionmaker instance returned by create_session_factory).
        """
        super().__init__(app)
        self._session_factory = session_factory

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        """Attach a fresh session to each request; close it after response.

        Args:
            request: Incoming Starlette Request.
            call_next: Next middleware / route handler in the chain.

        Returns:
            The HTTP Response from the downstream handler.
        """
        session = self._session_factory()
        request.state.db_session = session
        try:
            response = await call_next(request)
        finally:
            session.close()
        return response


class AsyncDbSessionMiddleware(BaseHTTPMiddleware):
    """Asynchronous SQLAlchemy session-per-request Starlette middleware.

    Notes/Architectural Intent:
        Creates a new AsyncSession for every HTTP request via an async_sessionmaker,
        exposing it as request.state.db_session. Handlers own commit/rollback via
        AsyncSqlAlchemyUnitOfWork — this middleware only manages lifecycle (open/close).
    """

    def __init__(
        self,
        app: ASGIApp,
        session_factory: Callable[[], Any],
    ) -> None:
        """Initialise with an async_sessionmaker callable.

        Args:
            app: The ASGI application to wrap.
            session_factory: A callable returning an AsyncSession
                (e.g. the async_sessionmaker returned by create_async_session_factory).
        """
        super().__init__(app)
        self._session_factory = session_factory

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        """Attach a fresh AsyncSession to each request; close it after response.

        Args:
            request: Incoming Starlette Request.
            call_next: Next middleware / route handler in the chain.

        Returns:
            The HTTP Response from the downstream handler.
        """
        session = self._session_factory()
        request.state.db_session = session
        try:
            response = await call_next(request)
        finally:
            await session.close()
        return response


def add_db_session_middleware(
    app: Any,
    session_factory: Callable[[], Any],
    *,
    async_mode: bool = False,
) -> None:
    """Convenience helper to attach the correct session middleware to a FastAPI app.

    Notes/Architectural Intent:
        Selects DbSessionMiddleware or AsyncDbSessionMiddleware based on async_mode.
        Intended to be called from the FastAPI bootstrapper or app factory when
        a session_factory is present in the DI container.

    Args:
        app: FastAPI / Starlette application instance.
        session_factory: Sessionmaker callable (sync or async).
        async_mode: If True, use AsyncDbSessionMiddleware.

    Returns:
        None.
    """
    if async_mode:
        app.add_middleware(AsyncDbSessionMiddleware, session_factory=session_factory)
    else:
        app.add_middleware(DbSessionMiddleware, session_factory=session_factory)


__all__ = [
    "AsyncDbSessionMiddleware",
    "DbSessionMiddleware",
    "add_db_session_middleware",
]
