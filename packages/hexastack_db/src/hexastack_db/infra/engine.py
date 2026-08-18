from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from hexastack_db.infra.config import HexastackDatabaseConfig, SqliteDialectConfig

__all__ = [
    "create_async_db_engine",
    "create_async_session_factory",
    "create_db_engine",
    "create_session_factory",
]


def _setup_sqlite_pragmas(engine: Engine, sqlite_cfg: SqliteDialectConfig) -> None:
    """Register connect event listener configuring SQLite PRAGMAs."""

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        if sqlite_cfg.foreign_keys:
            cursor.execute("PRAGMA foreign_keys=ON")
        if sqlite_cfg.busy_timeout_ms > 0:
            cursor.execute(f"PRAGMA busy_timeout={sqlite_cfg.busy_timeout_ms}")
        if sqlite_cfg.journal_mode:
            cursor.execute(f"PRAGMA journal_mode={sqlite_cfg.journal_mode}")
        if sqlite_cfg.synchronous:
            cursor.execute(f"PRAGMA synchronous={sqlite_cfg.synchronous}")
        cursor.close()


def create_async_db_engine(config: HexastackDatabaseConfig) -> AsyncEngine:
    """Create an asynchronous SQLAlchemy AsyncEngine from configuration.

    Notes/Architectural Intent:
        Automatically adapts standard SQLite or Postgres URLs to async drivers if omitted.

    Args:
        config: HexastackDatabaseConfig instance.

    Returns:
        Configured SQLAlchemy AsyncEngine.
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

    async_engine = create_async_engine(url, **kwargs)

    if "sqlite" in url:
        _setup_sqlite_pragmas(async_engine.sync_engine, config.sqlite)

    return async_engine


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


def create_db_engine(config: HexastackDatabaseConfig) -> Engine:
    """Create a synchronous SQLAlchemy Engine from configuration.

    Notes/Architectural Intent:
        Optimizes connection pooling for SQLite (StaticPool/NullPool for memory/file)
        and standard QueuePool for PostgreSQL/MySQL. Attaches dialect-specific PRAGMAs.

    Args:
        config: HexastackDatabaseConfig instance.

    Returns:
        Configured SQLAlchemy Engine.
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

    engine = create_engine(config.url, **kwargs)

    if config.is_sqlite:
        _setup_sqlite_pragmas(engine, config.sqlite)

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a thread-safe synchronous SQLAlchemy sessionmaker.

    Args:
        engine: The target SQLAlchemy Engine.

    Returns:
        Configured sessionmaker instance producing Sessions.
    """
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
