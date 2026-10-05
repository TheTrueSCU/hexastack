"""Unit tests for semantic vector caching adapters.

Notes/Architectural Intent:
    Tests SemanticVectorCache and AsyncSemanticVectorCache backed by in-memory
    vector memory adapters to verify cosine similarity cache hits, misses below
    threshold, TTL expiration, and structured JSON serialization.
"""

from __future__ import annotations

import time

import pytest

from hexastack_ai.adapters.cache.semantic import (
    AsyncSemanticVectorCache,
    SemanticVectorCache,
)
from hexastack_ai.adapters.memory.in_memory import (
    AsyncInMemoryVectorMemoryAdapter,
    InMemoryVectorMemoryAdapter,
)
from hexastack_ai.domain.memory import SemanticCacheConfig


def test_semantic_cache_exact_hit() -> None:
    """Test semantic cache hit with exact matching embedding."""
    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory, SemanticCacheConfig(similarity_threshold=0.9))

    emb = [1.0, 0.0, 0.0]
    cache.set(emb, {"answer": 42, "status": "ok"})

    res = cache.get(emb)
    assert res == {"answer": 42, "status": "ok"}


def test_semantic_cache_similar_hit() -> None:
    """Test semantic cache hit with slightly perturbed embedding exceeding threshold."""
    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory, SemanticCacheConfig(similarity_threshold=0.85))

    emb1 = [1.0, 0.0, 0.0]
    emb2 = [0.95, 0.1, 0.0]  # Very high cosine similarity
    cache.set(emb1, "Cached string result")

    res = cache.get(emb2)
    assert res == "Cached string result"


def test_semantic_cache_miss_below_threshold() -> None:
    """Test semantic cache miss when similarity is below threshold."""
    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory, SemanticCacheConfig(similarity_threshold=0.95))

    emb1 = [1.0, 0.0, 0.0]
    emb2 = [0.0, 1.0, 0.0]  # Orthogonal vector, similarity = 0.0
    cache.set(emb1, "Value")

    res = cache.get(emb2)
    assert res is None


def test_semantic_cache_ttl_expiration() -> None:
    """Test that expired semantic cache entries are evicted and return None."""
    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory, SemanticCacheConfig(ttl_seconds=1))

    emb = [1.0, 1.0, 1.0]
    cache.set(emb, "Expiring value", ttl_seconds=1)

    # Immediately available
    res_immediate = cache.get(emb)
    assert res_immediate == "Expiring value"

    # Simulate expiration by manipulating metadata in store
    for entry in memory._store.values():
        entry.metadata["expires_at"] = time.time() - 10

    res_expired = cache.get(emb)
    assert res_expired is None
    assert len(memory._store) == 0


def test_semantic_cache_clear() -> None:
    """Test clearing all cached semantic entries."""
    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory)

    cache.set([1.0, 0.0], "data 1")
    cache.set([0.0, 1.0], "data 2")
    assert len(memory._store) == 2

    cache.clear()
    assert len(memory._store) == 0


@pytest.mark.asyncio
async def test_async_semantic_cache() -> None:
    """Test asynchronous semantic vector cache operations."""
    async_memory = AsyncInMemoryVectorMemoryAdapter()
    cache = AsyncSemanticVectorCache(
        async_memory,
        SemanticCacheConfig(similarity_threshold=0.9, ttl_seconds=60),
    )

    emb = [0.5, 0.5, 0.0]
    await cache.set(emb, {"query": "test", "result": 123})

    # Exact hit
    hit = await cache.get(emb)
    assert hit == {"query": "test", "result": 123}

    # Miss orthogonal
    miss = await cache.get([0.0, 0.0, 1.0])
    assert miss is None

    # Expiration
    for entry in async_memory._sync_adapter._store.values():
        entry.metadata["expires_at"] = time.time() - 5

    expired = await cache.get(emb)
    assert expired is None

    # Set and clear
    await cache.set(emb, "fresh")
    await cache.clear()
    cleared = await cache.get(emb)
    assert cleared is None


def test_semantic_cache_type_preservation() -> None:
    """Verify semantic cache preserves string, integer, boolean, and list types without mutation."""
    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory)

    cache.set([1.0, 0.0], "123")
    val_str = cache.get([1.0, 0.0])
    assert val_str == "123"
    assert isinstance(val_str, str)

    cache.set([0.0, 1.0], "true")
    val_bool_str = cache.get([0.0, 1.0])
    assert val_bool_str == "true"
    assert isinstance(val_bool_str, str)

    cache.set([1.0, 1.0], 42)
    val_int = cache.get([1.0, 1.0])
    assert val_int == 42
    assert isinstance(val_int, int)

    cache.set([-1.0, 0.0], True)
    val_bool = cache.get([-1.0, 0.0])
    assert val_bool is True
    assert isinstance(val_bool, bool)


def test_semantic_cache_isolation_from_non_cache_entries() -> None:
    """Verify semantic cache skips memory entries not tagged as is_semantic_cache."""
    from hexastack_ai.domain.memory import MemoryEntry

    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory)

    # Store a non-cache memory entry (e.g. episodic chat memory)
    non_cache_entry = MemoryEntry(
        content="User likes python",
        embedding=[1.0, 0.0, 0.0],
        metadata={"category": "episodic"},
    )
    memory.store(non_cache_entry)

    # Cache get should ignore non-cache entries even on exact embedding match
    hit = cache.get([1.0, 0.0, 0.0])
    assert hit is None

    # Storing actual cache entry works alongside it
    cache.set([1.0, 0.0, 0.0], "cache-hit-payload")
    cache_hit = cache.get([1.0, 0.0, 0.0])
    assert cache_hit == "cache-hit-payload"
