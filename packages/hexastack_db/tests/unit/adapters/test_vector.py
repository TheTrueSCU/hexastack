import pytest
from hexastack_db.adapters.vector import (
    AsyncPgVectorStoreAdapter,
    PgVectorStoreAdapter,
    _cosine_similarity,
    create_vector_table,
)
from hexastack_db.infra.config import PgVectorConfig
from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def test_cosine_similarity_math():
    # Identical vectors
    assert pytest.approx(_cosine_similarity([1.0, 0.0], [1.0, 0.0])) == 1.0
    assert pytest.approx(_cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])) == 1.0

    # Orthogonal vectors
    assert pytest.approx(_cosine_similarity([1.0, 0.0], [0.0, 1.0])) == 0.0

    # Opposing vectors
    assert pytest.approx(_cosine_similarity([1.0, 0.0], [-1.0, 0.0])) == -1.0

    # Zero norm vectors (killing norm1 == 0.0 or norm2 == 0.0 mutants)
    assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert _cosine_similarity([1.0, 0.0], [0.0, 0.0]) == 0.0
    assert _cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_create_vector_table_caching():
    meta = MetaData()
    t1 = create_vector_table("my_vectors", dimension=128, metadata=meta)
    assert t1.name == "my_vectors"
    assert "id" in t1.c
    assert "embedding" in t1.c
    assert "metadata" in t1.c

    # Re-call returns cached table from metadata
    t2 = create_vector_table("my_vectors", dimension=128, metadata=meta)
    assert t1 is t2

    # None metadata creates fresh table
    t3 = create_vector_table("fresh_vectors", dimension=64, metadata=None)
    assert t3.name == "fresh_vectors"


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

    # Default constructor without explicit config
    default_adapter = PgVectorStoreAdapter(session_factory=factory)
    assert default_adapter._config.table_name == "hexastack_vectors"
    assert default_adapter._config.dimension == 1536

    # Upsert
    adapter.upsert("v1", [1.0, 0.0], {"doc": "x_axis"})
    adapter.upsert("v2", [0.0, 1.0], {"doc": "y_axis"})

    # Update existing
    adapter.upsert("v1", [1.0, 0.0], {"doc": "x_axis_updated"})

    # Get
    res = adapter.get("v1")
    assert res is not None
    v1_emb, v1_meta = res
    assert v1_emb == [1.0, 0.0]
    assert v1_meta == {"doc": "x_axis_updated"}

    # Get non-existent
    assert adapter.get("non_existent") is None

    # Search with ordering check
    results = adapter.search([0.99, 0.01], limit=2)
    assert len(results) == 2
    assert results[0]["_id"] == "v1"
    assert results[1]["_id"] == "v2"
    assert results[0]["_score"] > results[1]["_score"]

    # Delete
    assert adapter.delete("v1") is True
    assert adapter.delete("non_existent") is False
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

    # Default config constructor
    default_adapter = AsyncPgVectorStoreAdapter(session_factory=async_factory)
    assert default_adapter._config.table_name == "hexastack_vectors"
    assert default_adapter._config.dimension == 1536

    # Upsert
    await adapter.upsert_async("v1", [0.707, 0.707], {"title": "diagonal"})
    await adapter.upsert_async("v2", [1.0, 0.0], {"title": "horizontal"})

    # Update existing
    await adapter.upsert_async("v1", [0.707, 0.707], {"title": "diagonal_updated"})

    # Get
    res = await adapter.get_async("v1")
    assert res is not None
    emb, meta = res
    assert emb == [0.707, 0.707]
    assert meta == {"title": "diagonal_updated"}

    # Get non-existent
    assert await adapter.get_async("non_existent") is None

    # Search
    results = await adapter.search_async([0.707, 0.707], limit=2)
    assert len(results) == 2
    assert results[0]["_id"] == "v1"
    assert results[0]["_score"] > results[1]["_score"]

    # Delete
    assert await adapter.delete_async("v1") is True
    assert await adapter.delete_async("non_existent") is False
    assert await adapter.get_async("v1") is None

    # Clear
    await adapter.clear_async()
    assert len(await adapter.search_async([1.0, 0.0])) == 0
