"""Unit tests for Qdrant vector memory adapters.

Notes/Architectural Intent:
    Tests synchronous and asynchronous Qdrant vector memory adapters using
    mocked QdrantClient and AsyncQdrantClient instances to verify error handling,
    payload serialization, search translation, and collection lifecycle without
    requiring external network services.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hexastack_ai.adapters.memory.qdrant import (
    AsyncQdrantVectorMemoryAdapter,
    QdrantVectorMemoryAdapter,
)
from hexastack_ai.domain.exceptions import AiError
from hexastack_ai.domain.memory import MemoryEntry, QdrantConfig


def test_qdrant_adapter_init_defaults() -> None:
    """Test default initialization of synchronous Qdrant adapter."""
    adapter = QdrantVectorMemoryAdapter()
    config = adapter._config
    assert config.collection_name == "hexastack_memories"
    assert config.vector_size == 1536
    assert config.distance.lower() == "cosine"


def test_qdrant_adapter_lazy_client_init() -> None:
    """Test lazy client creation with custom URLs and locations."""
    with patch("hexastack_ai.adapters.memory.qdrant.require_dependency") as mock_req:
        mock_qc = MagicMock()
        mock_req.return_value = mock_qc

        # URL config
        cfg_url = QdrantConfig(
            url="http://localhost:6333",
            api_key="mock-token",  # pragma: allowlist secret
        )
        adapter_url = QdrantVectorMemoryAdapter(cfg_url)
        client_url = adapter_url._get_client()
        assert client_url is not None
        mock_qc.QdrantClient.assert_called_with(
            url="http://localhost:6333",
            api_key="mock-token",  # pragma: allowlist secret
        )

        # Path config
        cfg_path = QdrantConfig(path="/tmp/qdrant_test")
        adapter_path = QdrantVectorMemoryAdapter(cfg_path)
        client_path = adapter_path._get_client()
        assert client_path is not None
        mock_qc.QdrantClient.assert_called_with(path="/tmp/qdrant_test")

        # Memory config
        cfg_mem = QdrantConfig()
        adapter_mem = QdrantVectorMemoryAdapter(cfg_mem)
        client_mem = adapter_mem._get_client()
        assert client_mem is not None
        mock_qc.QdrantClient.assert_called_with(location=":memory:")


def test_qdrant_ensure_collection_creation() -> None:
    """Test collection creation when missing in synchronous adapter."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = False

    adapter = QdrantVectorMemoryAdapter(
        QdrantConfig(collection_name="test_col", distance="euclid"),
        client=mock_client,
    )
    client = adapter._get_client()
    assert client is mock_client
    mock_client.create_collection.assert_called_once()
    assert adapter._initialized is True

    # Calling again does not recreate
    mock_client.create_collection.reset_mock()
    adapter._ensure_collection_exists()
    mock_client.create_collection.assert_not_called()


def test_qdrant_ensure_collection_error_raises_ai_error() -> None:
    """Test that failure to verify or create collection raises AiError."""
    mock_client = MagicMock()
    mock_client.collection_exists.side_effect = RuntimeError("Qdrant offline")

    adapter = QdrantVectorMemoryAdapter(client=mock_client)
    with pytest.raises(AiError, match="Failed to verify or create Qdrant collection"):
        adapter._ensure_collection_exists()


def test_qdrant_store_success() -> None:
    """Test successful storage of a memory entry with embedding."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True

    adapter = QdrantVectorMemoryAdapter(client=mock_client)
    entry = MemoryEntry(
        id="mem-1",
        content="Important memory",
        embedding=[0.1, 0.2, 0.3],
        metadata={"category": "facts"},
    )
    result_id = adapter.store(entry)
    assert result_id == "mem-1"
    mock_client.upsert.assert_called_once()
    call_kwargs = mock_client.upsert.call_args.kwargs
    assert call_kwargs["collection_name"] == "hexastack_memories"
    point = call_kwargs["points"][0]
    assert point.id == "mem-1"
    assert point.payload["content"] == "Important memory"
    assert point.payload["category"] == "facts"


def test_qdrant_store_missing_embedding_raises() -> None:
    """Test that storing a memory entry without embedding raises AiError."""
    adapter = QdrantVectorMemoryAdapter(client=MagicMock())
    entry = MemoryEntry(id="mem-2", content="No vector")
    with pytest.raises(AiError, match="without an embedding"):
        adapter.store(entry)


def test_qdrant_store_upsert_failure_raises() -> None:
    """Test that upsert failures raise AiError."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True
    mock_client.upsert.side_effect = RuntimeError("Disk full")

    adapter = QdrantVectorMemoryAdapter(client=mock_client)
    entry = MemoryEntry(id="mem-3", content="Content", embedding=[0.5])
    with pytest.raises(AiError, match="Failed to upsert memory point"):
        adapter.store(entry)


def test_qdrant_search_query_points() -> None:
    """Test search using query_points API."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True

    mock_point = MagicMock()
    mock_point.id = "p-1"
    mock_point.score = 0.95
    mock_point.payload = {
        "content": "Found me",
        "source": "docs",
        "timestamp": "2026-09-10T12:00:00+00:00",
    }
    mock_point.vector = [0.1, 0.2]

    mock_response = MagicMock()
    mock_response.points = [mock_point]
    mock_client.query_points.return_value = mock_response

    adapter = QdrantVectorMemoryAdapter(client=mock_client)
    results = adapter.search([0.1, 0.2], limit=3, min_score=0.8)

    assert len(results) == 1
    assert results[0].entry.id == "p-1"
    assert results[0].entry.content == "Found me"
    assert results[0].entry.metadata["source"] == "docs"
    assert results[0].score == 0.95


def test_qdrant_search_fallback() -> None:
    """Test search fallback when query_points is unavailable."""
    mock_client = MagicMock(spec=["collection_exists", "search"])
    mock_client.collection_exists.return_value = True

    mock_point = MagicMock()
    mock_point.id = "p-2"
    mock_point.score = 0.88
    mock_point.payload = {"content": "Fallback match"}
    mock_point.vector = None
    mock_client.search.return_value = [mock_point]

    adapter = QdrantVectorMemoryAdapter(client=mock_client)
    results = adapter.search([0.5, 0.5])

    assert len(results) == 1
    assert results[0].entry.id == "p-2"
    assert results[0].entry.content == "Fallback match"
    assert results[0].score == 0.88


def test_qdrant_search_failure_raises() -> None:
    """Test that search failure raises AiError."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True
    mock_client.query_points.side_effect = RuntimeError("Bad query")

    adapter = QdrantVectorMemoryAdapter(client=mock_client)
    with pytest.raises(AiError, match="Qdrant vector search failed"):
        adapter.search([0.1, 0.2])


def test_qdrant_get() -> None:
    """Test retrieving entry by ID."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True

    mock_point = MagicMock()
    mock_point.id = "p-1"
    mock_point.payload = {
        "content": "Exact match",
        "timestamp": "2026-09-10T12:00:00+00:00",
    }
    mock_point.vector = [0.4, 0.5]
    mock_client.retrieve.return_value = [mock_point]

    adapter = QdrantVectorMemoryAdapter(client=mock_client)
    res = adapter.get("p-1")
    assert res is not None
    assert res.id == "p-1"
    assert res.content == "Exact match"
    assert res.embedding == [0.4, 0.5]

    mock_client.retrieve.return_value = []
    res_none = adapter.get("missing")
    assert res_none is None


def test_qdrant_get_failure_raises() -> None:
    """Test that retrieve failure raises AiError."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True
    mock_client.retrieve.side_effect = RuntimeError("Retrieval error")

    adapter = QdrantVectorMemoryAdapter(client=mock_client)
    with pytest.raises(AiError, match="Failed to retrieve point from Qdrant"):
        adapter.get("p-err")


def test_qdrant_delete_and_clear() -> None:
    """Test delete and clear methods."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True

    adapter = QdrantVectorMemoryAdapter(client=mock_client)
    res_del = adapter.delete("p-1")
    assert res_del is True
    mock_client.delete.assert_called_once()

    adapter.clear()
    mock_client.delete_collection.assert_called_once_with(
        collection_name="hexastack_memories"
    )


def test_qdrant_delete_and_clear_failures_raise() -> None:
    """Test that delete and clear failures raise AiError."""
    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True
    mock_client.delete.side_effect = RuntimeError("Delete err")
    mock_client.delete_collection.side_effect = RuntimeError("Clear err")

    adapter = QdrantVectorMemoryAdapter(client=mock_client)
    with pytest.raises(AiError, match="Failed to delete point from Qdrant"):
        adapter.delete("p-1")

    with pytest.raises(AiError, match="Failed to clear Qdrant collection"):
        adapter.clear()


@pytest.mark.asyncio
async def test_async_qdrant_adapter() -> None:
    """Test asynchronous Qdrant vector memory adapter operations."""
    mock_async_client = AsyncMock()
    mock_async_client.collection_exists.return_value = True

    adapter = AsyncQdrantVectorMemoryAdapter(client=mock_async_client)

    # Store
    entry = MemoryEntry(id="async-1", content="Async memory", embedding=[0.1, 0.2])
    store_id = await adapter.store(entry)
    assert store_id == "async-1"
    mock_async_client.upsert.assert_awaited_once()

    # Store missing embedding raises
    with pytest.raises(AiError, match="without an embedding"):
        await adapter.store(MemoryEntry(id="async-2", content="No emb"))

    # Search with query_points
    mock_point = MagicMock()
    mock_point.id = "async-1"
    mock_point.score = 0.99
    mock_point.payload = {
        "content": "Async result",
        "timestamp": "2026-09-10T12:00:00+00:00",
    }
    mock_point.vector = [0.1, 0.2]
    mock_resp = MagicMock()
    mock_resp.points = [mock_point]
    mock_async_client.query_points.return_value = mock_resp

    results = await adapter.search([0.1, 0.2])
    assert len(results) == 1
    assert results[0].entry.id == "async-1"
    assert results[0].score == 0.99

    # Search fallback
    mock_fallback_client = AsyncMock(spec=["collection_exists", "search"])
    mock_fallback_client.collection_exists.return_value = True
    mock_fallback_client.search.return_value = [mock_point]
    fallback_adapter = AsyncQdrantVectorMemoryAdapter(client=mock_fallback_client)
    fallback_results = await fallback_adapter.search([0.1, 0.2])
    assert len(fallback_results) == 1

    # Get
    mock_async_client.retrieve.return_value = [mock_point]
    retrieved = await adapter.get("async-1")
    assert retrieved is not None
    assert retrieved.id == "async-1"

    mock_async_client.retrieve.return_value = []
    missing = await adapter.get("async-missing")
    assert missing is None

    # Delete
    del_res = await adapter.delete("async-1")
    assert del_res is True

    # Clear
    await adapter.clear()
    mock_async_client.delete_collection.assert_awaited_once_with(
        collection_name="hexastack_memories"
    )


@pytest.mark.asyncio
async def test_async_qdrant_lazy_client_init() -> None:
    """Test lazy client creation for async Qdrant adapter."""
    with patch("hexastack_ai.adapters.memory.qdrant.require_dependency") as mock_req:
        mock_qc = MagicMock()
        mock_req.return_value = mock_qc

        # URL
        adapter_url = AsyncQdrantVectorMemoryAdapter(
            QdrantConfig(
                url="http://remote:6333",
                api_key="mock-token",  # pragma: allowlist secret
            )
        )
        c1 = adapter_url._get_client()
        assert c1 is not None
        mock_qc.AsyncQdrantClient.assert_called_with(
            url="http://remote:6333",
            api_key="mock-token",  # pragma: allowlist secret
        )

        # Path
        adapter_path = AsyncQdrantVectorMemoryAdapter(QdrantConfig(path="/tmp/test"))
        c2 = adapter_path._get_client()
        assert c2 is not None
        mock_qc.AsyncQdrantClient.assert_called_with(path="/tmp/test")

        # Memory
        adapter_mem = AsyncQdrantVectorMemoryAdapter(QdrantConfig())
        c3 = adapter_mem._get_client()
        assert c3 is not None
        mock_qc.AsyncQdrantClient.assert_called_with(location=":memory:")


@pytest.mark.asyncio
async def test_async_qdrant_ensure_collection_create() -> None:
    """Test async collection creation when collection does not exist."""
    mock_client = AsyncMock()
    mock_client.collection_exists.return_value = False

    adapter = AsyncQdrantVectorMemoryAdapter(
        QdrantConfig(collection_name="async_col", distance="dot"),
        client=mock_client,
    )
    await adapter._ensure_collection_exists()
    mock_client.create_collection.assert_awaited_once()
    assert adapter._initialized is True


@pytest.mark.asyncio
async def test_async_qdrant_errors_raise_ai_error() -> None:
    """Test error handling in async Qdrant adapter."""
    mock_client = AsyncMock()
    mock_client.collection_exists.return_value = True
    mock_client.upsert.side_effect = RuntimeError("Upsert error")
    mock_client.query_points.side_effect = RuntimeError("Search error")
    mock_client.retrieve.side_effect = RuntimeError("Retrieve error")
    mock_client.delete.side_effect = RuntimeError("Delete error")
    mock_client.delete_collection.side_effect = RuntimeError("Clear error")

    adapter = AsyncQdrantVectorMemoryAdapter(client=mock_client)
    entry = MemoryEntry(id="err", content="Content", embedding=[0.1])

    with pytest.raises(AiError, match="Failed to async upsert memory point"):
        await adapter.store(entry)

    with pytest.raises(AiError, match="Async Qdrant vector search failed"):
        await adapter.search([0.1])

    with pytest.raises(AiError, match="Failed to async retrieve point from Qdrant"):
        await adapter.get("err")

    with pytest.raises(AiError, match="Failed to async delete point from Qdrant"):
        await adapter.delete("err")

    with pytest.raises(AiError, match="Failed to async clear Qdrant collection"):
        await adapter.clear()

    # Collection check error
    err_client = AsyncMock()
    err_client.collection_exists.side_effect = RuntimeError("Net err")
    err_adapter = AsyncQdrantVectorMemoryAdapter(client=err_client)
    with pytest.raises(
        AiError, match="Failed to verify or create async Qdrant collection"
    ):
        await err_adapter._ensure_collection_exists()
