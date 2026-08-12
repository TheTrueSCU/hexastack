from hexastack_db.infra.config import HexastackDatabaseConfig
from hexastack_db.infra.engine import (
    create_async_db_engine,
    create_async_session_factory,
    create_db_engine,
    create_session_factory,
)
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine


def test_create_sync_engine_and_factory():
    cfg = HexastackDatabaseConfig(url="sqlite:///:memory:")
    engine = create_db_engine(cfg)
    assert isinstance(engine, Engine)

    factory = create_session_factory(engine)
    session = factory()
    assert session is not None
    session.close()
    engine.dispose()


def test_create_async_engine_and_factory():
    cfg = HexastackDatabaseConfig(url="sqlite+aiosqlite:///:memory:", async_mode=True)
    async_engine = create_async_db_engine(cfg)
    assert isinstance(async_engine, AsyncEngine)

    factory = create_async_session_factory(async_engine)
    session = factory()
    assert session is not None


def test_create_async_engine_auto_adapter():
    cfg = HexastackDatabaseConfig(url="sqlite:///:memory:", async_mode=True)
    async_engine = create_async_db_engine(cfg)
    assert "aiosqlite" in str(async_engine.url)
