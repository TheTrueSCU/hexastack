"""Unit tests for PgVectorMemoryAdapter bridging VectorStorePort to VectorMemoryPort.

Notes/Architectural Intent:
    Verifies that PgVectorMemoryAdapter faithfully translates MemoryEntry records
    to VectorStorePort upsert calls, unpacks search results, handles score filtering,
    and handles missing methods gracefully.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from hexastack_ai.adapters.memory.pgvector_bridge import PgVectorMemoryAdapter
from hexastack_ai.domain.exceptions import AiError
from hexastack_ai.domain.memory import MemoryEntry
from hexastack_core.ports.ai import VectorStorePort


def test_pgvector_store_success() -> None:
    """Test storing a memory entry into vector store."""
    mock_store = MagicMock(spec=VectorStorePort)
    adapter = PgVectorMemoryAdapter(mock_store)

    entry = MemoryEntry(
        id="pg-1",
        content="Postgres memory",
        embedding=[0.1, 0.2, 0.3],
        metadata={"user": "alice"},
    )
    result_id = adapter.store(entry)
    assert result_id == "pg-1"

    mock_store.upsert.assert_called_once()
    call_kwargs = mock_store.upsert.call_args.kwargs
    assert call_kwargs["vector_id"] == "pg-1"
    assert call_kwargs["embedding"] == [0.1, 0.2, 0.3]
    assert call_kwargs["metadata"]["content"] == "Postgres memory"
    assert call_kwargs["metadata"]["user"] == "alice"


def test_pgvector_store_missing_embedding_raises() -> None:
    """Test that storing without an embedding raises AiError."""
    mock_store = MagicMock(spec=VectorStorePort)
    adapter = PgVectorMemoryAdapter(mock_store)
    entry = MemoryEntry(id="pg-2", content="No vector")

    with pytest.raises(AiError, match="without an embedding"):
        adapter.store(entry)


def test_pgvector_store_underlying_failure_raises() -> None:
    """Test that vector store upsert failures raise AiError."""
    mock_store = MagicMock(spec=VectorStorePort)
    mock_store.upsert.side_effect = RuntimeError("DB connection lost")
    adapter = PgVectorMemoryAdapter(mock_store)

    entry = MemoryEntry(id="pg-3", content="Data", embedding=[0.5])
    with pytest.raises(AiError, match="Vector store upsert failed"):
        adapter.store(entry)


def test_pgvector_search() -> None:
    """Test searching vector store and filtering by score."""
    mock_store = MagicMock(spec=VectorStorePort)
    mock_store.search.return_value = [
        {
            "_id": "pg-1",
            "_score": 0.95,
            "content": "Match 1",
            "timestamp": "2026-09-10T10:00:00+00:00",
            "tag": "doc",
        },
        {
            "_id": "pg-2",
            "_score": 0.60,
            "content": "Match 2 low",
        },
    ]

    adapter = PgVectorMemoryAdapter(mock_store)
    results = adapter.search([0.1, 0.2], limit=5, min_score=0.8)

    assert len(results) == 1
    assert results[0].entry.id == "pg-1"
    assert results[0].entry.content == "Match 1"
    assert results[0].entry.metadata["tag"] == "doc"
    assert results[0].score == 0.95


def test_pgvector_search_failure_raises() -> None:
    """Test that search failure raises AiError."""
    mock_store = MagicMock(spec=VectorStorePort)
    mock_store.search.side_effect = RuntimeError("Query error")
    adapter = PgVectorMemoryAdapter(mock_store)

    with pytest.raises(AiError, match="Vector store search failed"):
        adapter.search([0.1])


def test_pgvector_get() -> None:
    """Test retrieving entry when underlying store implements get."""
    mock_store = MagicMock()
    mock_store.get.return_value = (
        [0.1, 0.2],
        {
            "content": "Found doc",
            "timestamp": "2026-09-10T12:00:00+00:00",
            "role": "admin",
        },
    )
    adapter = PgVectorMemoryAdapter(mock_store)

    entry = adapter.get("pg-1")
    assert entry is not None
    assert entry.id == "pg-1"
    assert entry.content == "Found doc"
    assert entry.embedding == [0.1, 0.2]
    assert entry.metadata["role"] == "admin"

    mock_store.get.return_value = None
    res_none = adapter.get("missing")
    assert res_none is None


def test_pgvector_get_unsupported() -> None:
    """Test retrieving entry when underlying store does not implement get."""
    bare_store = MagicMock(spec=["search", "upsert"])
    adapter = PgVectorMemoryAdapter(bare_store)
    res = adapter.get("any")
    assert res is None


def test_pgvector_delete() -> None:
    """Test deleting entry when supported and unsupported."""
    mock_store = MagicMock()
    mock_store.delete.return_value = True
    adapter = PgVectorMemoryAdapter(mock_store)

    res_del = adapter.delete("pg-1")
    assert res_del is True
    mock_store.delete.assert_called_once_with("pg-1")

    bare_store = MagicMock(spec=["search", "upsert"])
    bare_adapter = PgVectorMemoryAdapter(bare_store)
    res_unsupported = bare_adapter.delete("pg-1")
    assert res_unsupported is False


def test_pgvector_clear() -> None:
    """Test clearing store when supported and unsupported."""
    mock_store = MagicMock()
    adapter = PgVectorMemoryAdapter(mock_store)
    adapter.clear()
    mock_store.clear.assert_called_once()

    bare_store = MagicMock(spec=["search", "upsert"])
    bare_adapter = PgVectorMemoryAdapter(bare_store)
    # Should not raise AttributeError
    bare_adapter.clear()
