from pathlib import Path

from sqlalchemy import Engine, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import NullPool, StaticPool

from hexastack_core.testing.flags import require_extra
from hexastack_db.infra.config import (
    HexastackDatabaseConfig,
    SqliteDialectConfig,
)
from hexastack_db.infra.engine import (
    create_async_db_engine,
    create_async_session_factory,
    create_db_engine,
    create_session_factory,
)


@require_extra("aiosqlite")
def test_create_async_engine_and_factory():
    cfg = HexastackDatabaseConfig(url="sqlite+aiosqlite:///:memory:", async_mode=True)
    async_engine = create_async_db_engine(cfg)
    assert isinstance(async_engine, AsyncEngine)
    assert async_engine.pool.__class__ is StaticPool

    factory = create_async_session_factory(async_engine)
    session = factory()
    assert session is not None


@require_extra("aiosqlite")
def test_create_async_engine_auto_adapter():
    # SQLite URL rewrite
    cfg_sqlite = HexastackDatabaseConfig(url="sqlite:///:memory:", async_mode=True)
    async_engine_sqlite = create_async_db_engine(cfg_sqlite)
    assert "sqlite+aiosqlite:///:memory:" in str(async_engine_sqlite.url)

    # Postgres URL rewrite (without connecting)
    cfg_pg = HexastackDatabaseConfig(
        url="postgresql://usr:pwd@localhost:5432/testdb",
        async_mode=True,
        pool_size=12,
        max_overflow=18,
        pool_timeout=45,
        pool_recycle=900,
    )
    assert cfg_pg.is_postgres is True
    assert cfg_pg.is_sqlite is False
    assert cfg_pg.pool_size == 12
    assert cfg_pg.max_overflow == 18
    assert cfg_pg.pool_timeout == 45
    assert cfg_pg.pool_recycle == 900


@require_extra("aiosqlite")
def test_create_async_engine_file_null_pool(tmp_path: Path):
    db_file = tmp_path / "async_test.db"
    cfg = HexastackDatabaseConfig(url=f"sqlite:///{db_file}", async_mode=True)
    async_engine = create_async_db_engine(cfg)
    assert async_engine.pool.__class__ is NullPool


def test_create_sync_engine_and_factory_memory():
    cfg = HexastackDatabaseConfig(
        url="sqlite:///:memory:",
        echo=False,
        sqlite=SqliteDialectConfig(
            foreign_keys=True,
            busy_timeout_ms=3000,
            journal_mode="MEMORY",
            synchronous="OFF",
        ),
    )
    engine = create_db_engine(cfg)
    assert isinstance(engine, Engine)
    assert engine.pool.__class__ is StaticPool

    # Test PRAGMAs
    with engine.connect() as conn:
        fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert fk == 1
        busy = conn.execute(text("PRAGMA busy_timeout")).scalar()
        assert busy == 3000
        journal = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert str(journal).upper() == "MEMORY"
        sync = conn.execute(text("PRAGMA synchronous")).scalar()
        assert sync == 0  # OFF is 0

    factory = create_session_factory(engine)
    session = factory()
    assert session is not None
    session.close()
    engine.dispose()


def test_create_sync_engine_file_null_pool(tmp_path: Path):
    db_file = tmp_path / "test.db"
    cfg = HexastackDatabaseConfig(
        url=f"sqlite:///{db_file}",
        sqlite=SqliteDialectConfig(
            foreign_keys=False,
            busy_timeout_ms=0,
            journal_mode="WAL",
            synchronous="NORMAL",
        ),
    )
    engine = create_db_engine(cfg)
    assert engine.pool.__class__ is NullPool

    with engine.connect() as conn:
        fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert fk == 0
        journal = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert str(journal).upper() == "WAL"

    engine.dispose()
