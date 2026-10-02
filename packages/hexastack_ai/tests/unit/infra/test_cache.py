"""Unit tests for SemanticQueryCacheMiddleware in hexastack-ai.

Notes/Architectural Intent:
    Tests CQRS query interception, non-query bypass, missing embedding bypass,
    cache hit short-circuiting, sync/async handler resolution, and semantic
    cache population for both synchronous and asynchronous cache backends.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

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
from hexastack_ai.infra.cache import SemanticQueryCacheMiddleware
from hexastack_core.domain import Command, Query


class DummyCommand(Command):
    """Command for testing middleware bypass."""

    name: str = "do_something"


class DummyQueryWithoutVector(Query):
    """Query without vector embedding for testing bypass."""

    query_text: str = "hello"


class DummySemanticQuery(Query):
    """Query with vector embedding for semantic caching tests."""

    prompt: str = "What is the capital of France?"
    embedding: list[float] = [0.1, 0.2, 0.3]


class DummyQueryEmbeddingAttr(Query):
    """Query with query_embedding attribute."""

    prompt: str = "Test prompt"
    query_embedding: list[float] = [0.4, 0.5, 0.6]


def test_middleware_bypasses_non_query() -> None:
    """Test that commands and non-query messages bypass cache entirely."""
    cache = MagicMock(spec=SemanticVectorCache)
    middleware = SemanticQueryCacheMiddleware(cache)

    cmd = DummyCommand()
    next_call = MagicMock(return_value="executed_command")

    result = middleware(cmd, next_call)
    assert result == "executed_command"
    cache.get.assert_not_called()
    cache.set.assert_not_called()
    next_call.assert_called_once_with(cmd)


def test_middleware_bypasses_query_without_embedding() -> None:
    """Test that queries without vector embeddings bypass cache."""
    cache = MagicMock(spec=SemanticVectorCache)
    middleware = SemanticQueryCacheMiddleware(cache)

    query = DummyQueryWithoutVector()
    next_call = MagicMock(return_value="executed_plain_query")

    result = middleware(query, next_call)
    assert result == "executed_plain_query"
    cache.get.assert_not_called()
    next_call.assert_called_once_with(query)


def test_middleware_sync_cache_hit() -> None:
    """Test short-circuit on cache hit with synchronous cache."""
    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory)
    cache.set([0.1, 0.2, 0.3], "Paris is the capital")

    middleware = SemanticQueryCacheMiddleware(cache, similarity_threshold=0.9)
    query = DummySemanticQuery()
    next_call = MagicMock()

    result = middleware(query, next_call)
    assert result == "Paris is the capital"
    next_call.assert_not_called()


def test_middleware_sync_cache_miss_populates() -> None:
    """Test downstream execution and cache population on cache miss."""
    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory)

    middleware = SemanticQueryCacheMiddleware(cache, ttl_seconds=120)
    query = DummySemanticQuery()
    next_call = MagicMock(return_value="Paris")

    result = middleware(query, next_call)
    assert result == "Paris"
    next_call.assert_called_once_with(query)

    # Verify cached
    cached_val = cache.get([0.1, 0.2, 0.3])
    assert cached_val == "Paris"


def test_middleware_query_embedding_attr() -> None:
    """Test support for queries using query_embedding attribute."""
    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory)

    middleware = SemanticQueryCacheMiddleware(cache)
    query = DummyQueryEmbeddingAttr()
    next_call = MagicMock(return_value="Result from handler")

    result = middleware(query, next_call)
    assert result == "Result from handler"

    cached_val = cache.get([0.4, 0.5, 0.6])
    assert cached_val == "Result from handler"


@pytest.mark.asyncio
async def test_middleware_sync_cache_with_async_handler() -> None:
    """Test caching when downstream handler returns an awaitable coroutine."""
    memory = InMemoryVectorMemoryAdapter()
    cache = SemanticVectorCache(memory)

    middleware = SemanticQueryCacheMiddleware(cache)
    query = DummySemanticQuery()

    async def async_handler(_q: Any) -> str:
        return "Async handler result"

    coro_result = middleware(query, async_handler)
    resolved = await coro_result
    assert resolved == "Async handler result"

    cached_val = cache.get([0.1, 0.2, 0.3])
    assert cached_val == "Async handler result"


@pytest.mark.asyncio
async def test_middleware_async_cache() -> None:
    """Test middleware operating with an AsyncSemanticCachePort backend."""
    async_memory = AsyncInMemoryVectorMemoryAdapter()
    async_cache = AsyncSemanticVectorCache(
        async_memory, SemanticCacheConfig(similarity_threshold=0.9)
    )

    # Pre-populate
    await async_cache.set([0.1, 0.2, 0.3], "Pre-cached async")

    middleware = SemanticQueryCacheMiddleware(async_cache)
    query = DummySemanticQuery()
    next_call = MagicMock()

    # Hit
    hit = await middleware(query, next_call)
    assert hit == "Pre-cached async"
    next_call.assert_not_called()

    # Miss with new orthogonal vector
    new_query = DummySemanticQuery(embedding=[0.0, 0.0, -1.0])
    next_call_miss = MagicMock(return_value="Fresh async result")
    miss_res = await middleware(new_query, next_call_miss)
    assert miss_res == "Fresh async result"
    next_call_miss.assert_called_once_with(new_query)

    # Check cached
    verified_cache = await async_cache.get([0.0, 0.0, -1.0])
    assert verified_cache == "Fresh async result"


@pytest.mark.asyncio
async def test_middleware_async_cache_with_async_handler() -> None:
    """Test async cache when downstream handler is also async."""
    async_memory = AsyncInMemoryVectorMemoryAdapter()
    async_cache = AsyncSemanticVectorCache(async_memory)

    middleware = SemanticQueryCacheMiddleware(async_cache)
    query = DummySemanticQuery(embedding=[0.7, 0.8, 0.9])

    async def async_next(_q: Any) -> str:
        return "Async next executed"

    res = await middleware(query, async_next)
    assert res == "Async next executed"

    val = await async_cache.get([0.7, 0.8, 0.9])
    assert val == "Async next executed"
