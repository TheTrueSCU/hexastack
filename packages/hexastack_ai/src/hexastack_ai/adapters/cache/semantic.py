"""Semantic vector cache adapters for LLM inference and CQRS query caching.

Notes/Architectural Intent:
    Implements SemanticCachePort and AsyncSemanticCachePort by indexing query
    embeddings in a VectorMemoryPort or AsyncVectorMemoryPort. Enables sub-millisecond
    cache hits when subsequent queries are semantically equivalent (cosine similarity
    above a configurable threshold) without requiring identical query strings.
"""

from __future__ import annotations

import json
import time
from typing import Any

from hexastack_ai.domain.memory import MemoryEntry, SemanticCacheConfig
from hexastack_ai.ports.memory import (
    AsyncSemanticCachePort,
    AsyncVectorMemoryPort,
    SemanticCachePort,
    VectorMemoryPort,
)


class SemanticVectorCache(SemanticCachePort):
    """Synchronous semantic vector cache backed by a VectorMemoryPort.

    Notes/Architectural Intent:
        Intercepts requests with an embedding, computes similarity against previously
        cached entries, and returns the cached result if similarity exceeds the threshold
        and TTL has not expired.
    """

    def __init__(
        self,
        memory_store: VectorMemoryPort,
        config: SemanticCacheConfig | None = None,
    ) -> None:
        """Initialize semantic vector cache.

        Args:
            memory_store: Underlying VectorMemoryPort store.
            config: SemanticCacheConfig parameters (similarity threshold, TTL, capacity).
        """
        self._memory = memory_store
        self._config = config or SemanticCacheConfig()

    def get(
        self,
        query_embedding: list[float],
        threshold: float | None = None,
    ) -> Any | None:
        """Retrieve cached result matching query_embedding within threshold.

        Args:
            query_embedding: Floating-point query vector.
            threshold: Minimum cosine similarity score. Defaults to config value.

        Returns:
            The cached value if a fresh match meets the threshold, else None.
        """
        cutoff = (
            threshold if threshold is not None else self._config.similarity_threshold
        )
        matches = self._memory.search(
            query_embedding=query_embedding,
            limit=1,
            min_score=cutoff,
        )
        if not matches:
            return None

        best_match = matches[0]
        meta = best_match.entry.metadata
        expires_at = meta.get("expires_at")
        if expires_at is not None and time.time() > expires_at:
            self._memory.delete(best_match.entry.id)
            return None

        raw_val = best_match.entry.content
        try:
            return json.loads(raw_val)
        except Exception:
            return raw_val

    def set(
        self,
        query_embedding: list[float],
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a result value in the semantic cache.

        Args:
            query_embedding: Floating-point query vector.
            value: The result payload to cache.
            ttl_seconds: Optional duration before expiry in seconds.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._config.ttl_seconds
        expires_at = (time.time() + ttl) if ttl > 0 else None

        serialized = json.dumps(value) if not isinstance(value, str) else value
        metadata: dict[str, Any] = {
            "is_semantic_cache": True,
            "created_at": time.time(),
        }
        if expires_at is not None:
            metadata["expires_at"] = expires_at

        entry = MemoryEntry(
            content=serialized,
            embedding=query_embedding,
            metadata=metadata,
        )
        self._memory.store(entry)

    def clear(self) -> None:
        """Clear all entries from the semantic cache."""
        self._memory.clear()


class AsyncSemanticVectorCache(AsyncSemanticCachePort):
    """Asynchronous semantic vector cache backed by an AsyncVectorMemoryPort.

    Notes/Architectural Intent:
        Asynchronous variant enabling non-blocking similarity cache lookups
        in async agent pipelines and web handlers.
    """

    def __init__(
        self,
        memory_store: AsyncVectorMemoryPort,
        config: SemanticCacheConfig | None = None,
    ) -> None:
        """Initialize async semantic vector cache.

        Args:
            memory_store: Underlying AsyncVectorMemoryPort store.
            config: SemanticCacheConfig parameters.
        """
        self._memory = memory_store
        self._config = config or SemanticCacheConfig()

    async def get(
        self,
        query_embedding: list[float],
        threshold: float | None = None,
    ) -> Any | None:
        """Retrieve cached result asynchronously matching query_embedding.

        Args:
            query_embedding: Floating-point query vector.
            threshold: Minimum cosine similarity score.

        Returns:
            The cached value if a fresh match meets the threshold, else None.
        """
        cutoff = (
            threshold if threshold is not None else self._config.similarity_threshold
        )
        matches = await self._memory.search(
            query_embedding=query_embedding,
            limit=1,
            min_score=cutoff,
        )
        if not matches:
            return None

        best_match = matches[0]
        meta = best_match.entry.metadata
        expires_at = meta.get("expires_at")
        if expires_at is not None and time.time() > expires_at:
            await self._memory.delete(best_match.entry.id)
            return None

        raw_val = best_match.entry.content
        try:
            return json.loads(raw_val)
        except Exception:
            return raw_val

    async def set(
        self,
        query_embedding: list[float],
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a result value asynchronously in the semantic cache.

        Args:
            query_embedding: Floating-point query vector.
            value: The result payload to cache.
            ttl_seconds: Optional duration before expiry in seconds.
        """
        ttl = ttl_seconds if ttl_seconds is not None else self._config.ttl_seconds
        expires_at = (time.time() + ttl) if ttl > 0 else None

        serialized = json.dumps(value) if not isinstance(value, str) else value
        metadata: dict[str, Any] = {
            "is_semantic_cache": True,
            "created_at": time.time(),
        }
        if expires_at is not None:
            metadata["expires_at"] = expires_at

        entry = MemoryEntry(
            content=serialized,
            embedding=query_embedding,
            metadata=metadata,
        )
        await self._memory.store(entry)

    async def clear(self) -> None:
        """Clear all entries asynchronously from the semantic cache."""
        await self._memory.clear()


__all__ = [
    "AsyncSemanticVectorCache",
    "SemanticVectorCache",
]
