"""Unit tests for AI agent long-term vector memory domain models."""

from datetime import UTC, datetime

from hexastack_ai.domain.memory import (
    MemoryEntry,
    MemorySearchResult,
    QdrantConfig,
    SemanticCacheConfig,
)


def test_memory_entry_defaults() -> None:
    """Verify MemoryEntry default field values and initialization."""
    entry = MemoryEntry(content="User prefers Python and Hexagonal architecture.")

    assert entry.content == "User prefers Python and Hexagonal architecture."
    assert entry.id is not None
    assert len(entry.id) > 0
    assert entry.embedding is None
    assert entry.metadata == {}
    assert isinstance(entry.timestamp, datetime)


def test_memory_entry_with_embedding_and_metadata() -> None:
    """Verify MemoryEntry with explicit embedding and metadata."""
    now = datetime.now(UTC)
    entry = MemoryEntry(
        id="mem-123",
        content="Deploy to AWS us-east-1",
        embedding=[0.1, 0.2, 0.3],
        metadata={"category": "infra", "importance": 5},
        timestamp=now,
    )

    assert entry.id == "mem-123"
    assert entry.content == "Deploy to AWS us-east-1"
    assert entry.embedding == [0.1, 0.2, 0.3]
    assert entry.metadata["category"] == "infra"
    assert entry.metadata["importance"] == 5
    assert entry.timestamp == now


def test_memory_search_result() -> None:
    """Verify MemorySearchResult encapsulates entry and relevance score."""
    entry = MemoryEntry(content="FastAPI dependency injection")
    result = MemorySearchResult(entry=entry, score=0.95)

    assert result.entry.content == "FastAPI dependency injection"
    assert result.score == 0.95


def test_semantic_cache_config_defaults() -> None:
    """Verify SemanticCacheConfig default parameter values."""
    config = SemanticCacheConfig()

    assert config.similarity_threshold == 0.90
    assert config.ttl_seconds == 3600
    assert config.max_entries == 1000


def test_qdrant_config_defaults() -> None:
    """Verify QdrantConfig default connection settings."""
    config = QdrantConfig()

    assert config.collection_name == "hexastack_memories"
    assert config.vector_size == 1536
    assert config.distance == "Cosine"
    assert config.location == ":memory:"
    assert config.url is None
    assert config.api_key is None
    assert config.path is None
