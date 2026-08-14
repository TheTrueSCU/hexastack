import time
from datetime import datetime

import pytest
from sqlalchemy import DateTime, String, create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from hexastack_db.adapters.repository import (
    AsyncSqlAlchemyRepository,
    SqlAlchemyRepository,
)
from hexastack_db.infra.mixins import (
    HexastackBase,
    TimestampMixin,
    UuidPrimaryKeyMixin,
)


class ArticleRecord(UuidPrimaryKeyMixin, TimestampMixin, HexastackBase):
    __tablename__ = "test_articles"

    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(2000), default="")


def _sync_engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_mixin_column_definitions():
    tbl = ArticleRecord.__table__
    id_col = tbl.c.id
    assert isinstance(id_col.type, String)
    assert id_col.type.length == 36
    assert id_col.primary_key is True

    created_col = tbl.c.created_at
    assert isinstance(created_col.type, DateTime)
    assert created_col.type.timezone is True
    assert created_col.nullable is False

    updated_col = tbl.c.updated_at
    assert isinstance(updated_col.type, DateTime)
    assert updated_col.type.timezone is True
    assert updated_col.nullable is False


def test_uuid_primary_key_mixin_generates_unique_ids():
    engine = _sync_engine()
    HexastackBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session: Session = factory()

    repo = SqlAlchemyRepository(session=session, model_cls=ArticleRecord)
    a1 = ArticleRecord(title="First")
    a2 = ArticleRecord(title="Second")
    repo.add(a1)
    repo.add(a2)

    assert a1.id is not None
    assert a2.id is not None
    assert a1.id != a2.id
    # IDs should be UUID-format strings
    assert len(a1.id) == 36
    assert a1.id.count("-") == 4

    session.close()
    engine.dispose()


def test_timestamp_mixin_sets_created_at_and_updated_at():
    engine = _sync_engine()
    HexastackBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session: Session = factory()

    repo = SqlAlchemyRepository(session=session, model_cls=ArticleRecord)
    article = ArticleRecord(title="Timestamps Test")
    repo.add(article)
    session.commit()

    assert isinstance(article.created_at, datetime)
    assert isinstance(article.updated_at, datetime)
    assert article.created_at <= article.updated_at

    session.close()
    engine.dispose()


def test_timestamp_mixin_updated_at_refreshed_on_update():
    engine = _sync_engine()
    HexastackBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session: Session = factory()

    repo = SqlAlchemyRepository(session=session, model_cls=ArticleRecord)
    article = ArticleRecord(title="Update Test")
    repo.add(article)
    session.commit()

    # Small sleep to ensure timestamp difference is observable
    time.sleep(0.01)
    article.title = "Updated Title"
    repo.update(article)
    session.commit()

    refetched = repo.get(article.id)
    assert refetched is not None
    # created_at must not change
    assert refetched.created_at == article.created_at

    session.close()
    engine.dispose()


def test_hexastack_base_metadata_contains_table():
    table_names = [t.name for t in HexastackBase.metadata.sorted_tables]
    assert "test_articles" in table_names


@pytest.mark.anyio
async def test_mixin_async_repository():
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with async_engine.begin() as conn:
        await conn.run_sync(HexastackBase.metadata.create_all)

    async_factory = async_sessionmaker(bind=async_engine)
    async with async_factory() as session:
        repo = AsyncSqlAlchemyRepository(session=session, model_cls=ArticleRecord)
        a = ArticleRecord(title="Async UUID Mixin Test")
        await repo.add(a)

        assert a.id is not None
        assert len(a.id) == 36
        assert isinstance(a.created_at, datetime)
        assert isinstance(a.updated_at, datetime)

        fetched = await repo.get(a.id)
        assert fetched is not None
        assert fetched.title == "Async UUID Mixin Test"

    await async_engine.dispose()
