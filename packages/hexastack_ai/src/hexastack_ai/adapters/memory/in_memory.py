"""In-memory vector memory adapters with exact cosine similarity matching.

Notes/Architectural Intent:
    Provides dictionary-backed vector memory storage with thread-safe locking
    and exact cosine similarity calculation for local testing, development,
    and ephemeral agent execution without external vector database dependencies.
"""

from __future__ import annotations

import math
import threading

from hexastack_ai.domain.memory import MemoryEntry, MemorySearchResult
from hexastack_ai.ports.memory import AsyncVectorMemoryPort, VectorMemoryPort


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate the cosine similarity between two floating point vectors."""
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm1 * norm2)))


class InMemoryVectorMemoryAdapter(VectorMemoryPort):
    """Synchronous in-memory vector memory adapter.

    Notes/Architectural Intent:
        Implements VectorMemoryPort using a Python dictionary and an RLock,
        ideal for testing agent memory recall loops with zero external infrastructure.
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory vector memory store."""
        self._store: dict[str, MemoryEntry] = {}
        self._lock = threading.RLock()

    def store(self, entry: MemoryEntry) -> str:
        """Persist a memory entry and return its ID.

        Args:
            entry: MemoryEntry record to store.

        Returns:
            The ID of the stored memory entry.
        """
        with self._lock:
            self._store[entry.id] = entry
            return entry.id

    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[MemorySearchResult]:
        """Search memories using cosine similarity against stored embeddings.

        Args:
            query_embedding: Floating-point query vector.
            limit: Maximum number of ranked results to return.
            min_score: Minimum similarity score cutoff.

        Returns:
            List of MemorySearchResult instances sorted by relevance descending.
        """
        results: list[MemorySearchResult] = []
        with self._lock:
            for entry in self._store.values():
                if entry.embedding is None:
                    continue
                score = _cosine_similarity(query_embedding, entry.embedding)
                if score >= min_score:
                    results.append(MemorySearchResult(entry=entry, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def get(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry by ID.

        Args:
            memory_id: Unique identifier string.

        Returns:
            MemoryEntry if present, else None.
        """
        with self._lock:
            return self._store.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory entry by ID.

        Args:
            memory_id: Unique identifier string.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            return self._store.pop(memory_id, None) is not None

    def clear(self) -> None:
        """Clear all stored memory entries."""
        with self._lock:
            self._store.clear()


class AsyncInMemoryVectorMemoryAdapter(AsyncVectorMemoryPort):
    """Asynchronous in-memory vector memory adapter.

    Notes/Architectural Intent:
        Implements AsyncVectorMemoryPort delegating internally to a thread-safe
        memory store, enabling async/await patterns without external services.
    """

    def __init__(self) -> None:
        """Initialize an empty asynchronous in-memory vector memory store."""
        self._sync_adapter = InMemoryVectorMemoryAdapter()

    async def store(self, entry: MemoryEntry) -> str:
        """Persist a memory entry asynchronously.

        Args:
            entry: MemoryEntry record to store.

        Returns:
            The ID of the stored memory entry.
        """
        return self._sync_adapter.store(entry)

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[MemorySearchResult]:
        """Search stored memories asynchronously by embedding cosine similarity.

        Args:
            query_embedding: Floating-point query vector.
            limit: Maximum number of ranked results to return.
            min_score: Minimum similarity score cutoff.

        Returns:
            List of MemorySearchResult instances sorted by relevance descending.
        """
        return self._sync_adapter.search(
            query_embedding=query_embedding,
            limit=limit,
            min_score=min_score,
        )

    async def get(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry asynchronously by ID.

        Args:
            memory_id: Unique identifier string.

        Returns:
            MemoryEntry if present, else None.
        """
        return self._sync_adapter.get(memory_id)

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry asynchronously by ID.

        Args:
            memory_id: Unique identifier string.

        Returns:
            True if deleted, False if not found.
        """
        return self._sync_adapter.delete(memory_id)

    async def clear(self) -> None:
        """Clear all stored memory entries asynchronously."""
        self._sync_adapter.clear()


__all__ = [
    "AsyncInMemoryVectorMemoryAdapter",
    "InMemoryVectorMemoryAdapter",
]
