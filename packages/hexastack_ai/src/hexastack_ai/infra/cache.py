"""Semantic Query Caching Middleware for CQRS Pipelines in hexastack-ai.

Notes/Architectural Intent:
    Provides pipeline interceptors that inspect Query messages for vector embeddings
    or semantic representations, querying a SemanticCachePort before executing downstream
    handlers. On cache hits exceeding the similarity threshold, short-circuits execution
    and returns cached payloads.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, TypeVar, cast

from hexastack_ai.ports.memory import AsyncSemanticCachePort, SemanticCachePort
from hexastack_core.domain import Generic, Query

G = TypeVar("G", bound=Generic)
R = TypeVar("R")


def _extract_query_embedding(query: Any) -> list[float] | None:
    """Extract embedding vector from a query instance if present."""
    if hasattr(query, "embedding") and isinstance(query.embedding, list):
        return query.embedding
    if hasattr(query, "query_embedding") and isinstance(query.query_embedding, list):
        return query.query_embedding
    return None


class SemanticQueryCacheMiddleware:
    """CQRS pipeline middleware providing semantic vector caching for queries.

    Notes/Architectural Intent:
        Short-circuits expensive LLM calls or complex analytical database aggregations
        when an incoming Query message has a semantic embedding with high cosine similarity
        to a previously executed query.
    """

    def __init__(
        self,
        cache: SemanticCachePort | AsyncSemanticCachePort,
        similarity_threshold: float | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Initialize middleware with cache port and optional overrides.

        Args:
            cache: Synchronous or asynchronous SemanticCachePort adapter.
            similarity_threshold: Optional similarity cutoff (e.g. 0.92).
            ttl_seconds: Optional time-to-live in seconds for cached entries.
        """
        self._cache = cache
        self._threshold = similarity_threshold
        self._ttl_seconds = ttl_seconds

    def __call__(self, instance: G, next_call: Callable[[G], R]) -> Any:
        """Intercept query execution, check semantic cache, and populate on miss.

        Args:
            instance: Message instance being dispatched through pipeline.
            next_call: Next callable in the pipeline chain.

        Returns:
            Result payload or coroutine.
        """
        if not isinstance(instance, Query):
            return next_call(instance)

        embedding = _extract_query_embedding(instance)
        if embedding is None:
            return next_call(instance)

        if isinstance(self._cache, AsyncSemanticCachePort):
            return cast("R", self._handle_async(instance, next_call, embedding))

        cached_val = self._cache.get(embedding, threshold=self._threshold)
        if cached_val is not None:
            return cast("R", cached_val)

        result = next_call(instance)
        if inspect.iscoroutine(result):
            return cast("R", self._await_and_cache(result, embedding))

        if result is not None:
            self._cache.set(embedding, result, ttl_seconds=self._ttl_seconds)

        return result

    async def _handle_async(
        self,
        instance: G,
        next_call: Callable[[G], R],
        embedding: list[float],
    ) -> Any:
        """Handle asynchronous semantic cache lookup and population."""
        async_cache = cast("AsyncSemanticCachePort", self._cache)
        cached_val = await async_cache.get(embedding, threshold=self._threshold)
        if cached_val is not None:
            return cached_val

        raw_result = next_call(instance)
        if inspect.iscoroutine(raw_result):
            result = await raw_result
        else:
            result = raw_result

        if result is not None:
            await async_cache.set(embedding, result, ttl_seconds=self._ttl_seconds)

        return result

    async def _await_and_cache(
        self,
        coro: Any,
        embedding: list[float],
    ) -> Any:
        """Await downstream handler coroutine and store result synchronously."""
        sync_cache = cast("SemanticCachePort", self._cache)
        result = await coro
        if result is not None:
            sync_cache.set(embedding, result, ttl_seconds=self._ttl_seconds)
        return result


__all__ = [
    "SemanticQueryCacheMiddleware",
]
