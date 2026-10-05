"""Unit tests for InMemoryVectorMemoryAdapter and AsyncInMemoryVectorMemoryAdapter."""

import pytest

from hexastack_ai.adapters.memory.in_memory import (
    AsyncInMemoryVectorMemoryAdapter,
    InMemoryVectorMemoryAdapter,
    _cosine_similarity,
)
from hexastack_ai.domain.memory import MemoryEntry


def test_cosine_similarity_edge_cases() -> None:
    """Verify cosine similarity calculation with zero, orthogonal, and identical vectors."""
    sim_identical = _cosine_similarity([1.0, 0.0], [1.0, 0.0])
    assert sim_identical == pytest.approx(1.0)

    sim_orthogonal = _cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert sim_orthogonal == pytest.approx(0.0)

    sim_zero = _cosine_similarity([0.0, 0.0], [1.0, 2.0])
    assert sim_zero == 0.0

    sim_both_zero = _cosine_similarity([0.0, 0.0], [0.0, 0.0])
    assert sim_both_zero == 0.0


def test_in_memory_vector_memory_crud_lifecycle() -> None:
    """Verify store, get, search, delete, and clear operations on InMemoryVectorMemoryAdapter."""
    adapter = InMemoryVectorMemoryAdapter()

    entry1 = MemoryEntry(
        id="mem-001",
        content="Antigravity coding assistant",
        embedding=[1.0, 0.0, 0.0],
        metadata={"category": "ai"},
    )
    entry2 = MemoryEntry(
        id="mem-002",
        content="PostgreSQL database adapter",
        embedding=[0.0, 1.0, 0.0],
        metadata={"category": "db"},
    )
    entry3 = MemoryEntry(
        id="mem-003",
        content="Antigravity agentic workflows",
        embedding=[0.9, 0.1, 0.0],
        metadata={"category": "ai"},
    )
    entry_no_vec = MemoryEntry(
        id="mem-004",
        content="Entry without embedding",
        embedding=None,
    )

    stored_id1 = adapter.store(entry1)
    assert stored_id1 == "mem-001"
    stored_id2 = adapter.store(entry2)
    assert stored_id2 == "mem-002"
    stored_id3 = adapter.store(entry3)
    assert stored_id3 == "mem-003"
    stored_id4 = adapter.store(entry_no_vec)
    assert stored_id4 == "mem-004"

    fetched = adapter.get("mem-001")
    assert fetched is not None
    assert fetched.content == "Antigravity coding assistant"

    fetched_missing = adapter.get("mem-nonexistent")
    assert fetched_missing is None

    # Search with query vector closest to mem-001 and mem-003
    query_vec = [1.0, 0.05, 0.0]
    results = adapter.search(query_vec, limit=2, min_score=0.5)
    assert len(results) == 2
    assert results[0].entry.id in ("mem-001", "mem-003")
    assert results[0].score >= results[1].score

    # Search with high threshold excluding mem-002
    ai_only = adapter.search([1.0, 0.0, 0.0], limit=5, min_score=0.8)
    assert len(ai_only) == 2
    ids = [r.entry.id for r in ai_only]
    assert "mem-001" in ids
    assert "mem-003" in ids
    assert "mem-002" not in ids

    # Deletion
    del_res = adapter.delete("mem-001")
    assert del_res is True
    assert adapter.get("mem-001") is None

    del_missing = adapter.delete("mem-001")
    assert del_missing is False

    # Clear
    adapter.clear()
    assert adapter.get("mem-002") is None
    assert adapter.get("mem-003") is None
    empty_results = adapter.search([1.0, 0.0, 0.0])
    assert len(empty_results) == 0


@pytest.mark.asyncio
async def test_async_in_memory_vector_memory_crud_lifecycle() -> None:
    """Verify asynchronous CRUD operations on AsyncInMemoryVectorMemoryAdapter."""
    adapter = AsyncInMemoryVectorMemoryAdapter()

    entry = MemoryEntry(
        id="async-001",
        content="Asynchronous event bus integration",
        embedding=[0.5, 0.5, 0.0],
        metadata={"priority": "high"},
    )

    stored_id = await adapter.store(entry)
    assert stored_id == "async-001"

    fetched = await adapter.get("async-001")
    assert fetched is not None
    assert fetched.content == "Asynchronous event bus integration"

    results = await adapter.search([0.5, 0.5, 0.0], limit=1, min_score=0.9)
    assert len(results) == 1
    assert results[0].entry.id == "async-001"
    assert results[0].score == pytest.approx(1.0)

    deleted = await adapter.delete("async-001")
    assert deleted is True

    await adapter.clear()
    cleared = await adapter.get("async-001")
    assert cleared is None
