from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from hexastack_db.infra.config import HexastackDatabaseConfig


def create_db_engine(config: HexastackDatabaseConfig) -> Engine:
    """Create a synchronous SQLAlchemy Engine from configuration.

    Notes/Architectural Intent:
        Optimizes connection pooling for SQLite (StaticPool/NullPool for memory/file)
        and standard QueuePool for PostgreSQL/MySQL.

    Args:
        config: HexastackDatabaseConfig instance.

    Returns:
        Configured SQLAlchemy Engine.

    Raises:
        None.
    """
    kwargs: dict[str, Any] = {"echo": config.echo}

    if config.is_sqlite:
        if ":memory:" in config.url:
            kwargs["connect_args"] = {"check_same_thread": False}
            kwargs["poolclass"] = StaticPool
        else:
            kwargs["connect_args"] = {"check_same_thread": False}
            kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = config.pool_size
        kwargs["max_overflow"] = config.max_overflow
        kwargs["pool_timeout"] = config.pool_timeout
        kwargs["pool_recycle"] = config.pool_recycle

    return create_engine(config.url, **kwargs)


def create_async_db_engine(config: HexastackDatabaseConfig) -> AsyncEngine:
    """Create an asynchronous SQLAlchemy AsyncEngine from configuration.

    Notes/Architectural Intent:
        Automatically adapts standard SQLite or Postgres URLs to async drivers if omitted.

    Args:
        config: HexastackDatabaseConfig instance.

    Returns:
        Configured SQLAlchemy AsyncEngine.

    Raises:
        None.
    """
    url = config.url
    if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    elif url.startswith("postgresql://") and not url.startswith(
        "postgresql+asyncpg://"
    ):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    kwargs: dict[str, Any] = {"echo": config.echo}

    if "sqlite" in url:
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
        else:
            kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = config.pool_size
        kwargs["max_overflow"] = config.max_overflow
        kwargs["pool_timeout"] = config.pool_timeout
        kwargs["pool_recycle"] = config.pool_recycle

    return create_async_engine(url, **kwargs)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a thread-safe synchronous SQLAlchemy sessionmaker.

    Args:
        engine: The target SQLAlchemy Engine.

    Returns:
        Configured sessionmaker instance producing Sessions.
    """
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_async_session_factory(
    async_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an asynchronous SQLAlchemy async_sessionmaker.

    Args:
        async_engine: The target SQLAlchemy AsyncEngine.

    Returns:
        Configured async_sessionmaker instance producing AsyncSessions.
    """
    return async_sessionmaker(
        bind=async_engine, autoflush=False, expire_on_commit=False
    )


__all__ = [
    "create_async_db_engine",
    "create_async_session_factory",
    "create_db_engine",
    "create_session_factory",
]
