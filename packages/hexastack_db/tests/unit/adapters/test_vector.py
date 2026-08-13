import pytest
from hexastack_db.adapters.vector import (
    AsyncPgVectorStoreAdapter,
    PgVectorStoreAdapter,
)
from hexastack_db.infra.config import PgVectorConfig
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def test_pg_vector_store_adapter_sync():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine)
    config = PgVectorConfig(table_name="test_vectors", dimension=2)

    adapter = PgVectorStoreAdapter(session_factory=factory, config=config)
    adapter.create_table()

    # Upsert
    adapter.upsert("v1", [1.0, 0.0], {"doc": "x_axis"})
    adapter.upsert("v2", [0.0, 1.0], {"doc": "y_axis"})

    # Get
    res = adapter.get("v1")
    assert res is not None
    v1_emb, v1_meta = res
    assert v1_emb == [1.0, 0.0]
    assert v1_meta == {"doc": "x_axis"}

    # Search
    results = adapter.search([0.99, 0.01], limit=1)
    assert len(results) == 1
    assert results[0]["_id"] == "v1"
    assert results[0]["doc"] == "x_axis"

    # Delete
    assert adapter.delete("v1") is True
    assert adapter.get("v1") is None

    # Clear
    adapter.clear()
    assert len(adapter.search([0.0, 1.0])) == 0


@pytest.mark.anyio
async def test_async_pg_vector_store_adapter():
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async_factory = async_sessionmaker(bind=async_engine)
    config = PgVectorConfig(table_name="test_async_vectors", dimension=2)

    adapter = AsyncPgVectorStoreAdapter(session_factory=async_factory, config=config)
    await adapter.create_table_async()

    # Upsert
    await adapter.upsert_async("v1", [0.707, 0.707], {"title": "diagonal"})
    await adapter.upsert_async("v2", [1.0, 0.0], {"title": "horizontal"})

    # Get
    res = await adapter.get_async("v1")
    assert res is not None
    emb, meta = res
    assert emb == [0.707, 0.707]
    assert meta == {"title": "diagonal"}

    # Search
    results = await adapter.search_async([0.707, 0.707], limit=1)
    assert len(results) == 1
    assert results[0]["_id"] == "v1"

    # Delete
    assert await adapter.delete_async("v1") is True
    assert await adapter.get_async("v1") is None

    # Clear
    await adapter.clear_async()
    assert len(await adapter.search_async([1.0, 0.0])) == 0
