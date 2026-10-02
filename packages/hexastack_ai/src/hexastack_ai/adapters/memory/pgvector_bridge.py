"""Bridge adapter adapting VectorStorePort to VectorMemoryPort.

Notes/Architectural Intent:
    Allows applications using PostgreSQL pgvector (e.g. PgVectorStoreAdapter from
    hexastack-db) or any generic VectorStorePort implementation to be used
    directly as an AI agent long-term memory backend without duplicate code.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from hexastack_ai.domain.exceptions import AiError
from hexastack_ai.domain.memory import MemoryEntry, MemorySearchResult
from hexastack_ai.ports.memory import VectorMemoryPort
from hexastack_core.ports.ai import VectorStorePort


class PgVectorMemoryAdapter(VectorMemoryPort):
    """Bridges any VectorStorePort implementation to the VectorMemoryPort contract.

    Notes/Architectural Intent:
        Serializes MemoryEntry content and timestamps transparently into the underlying
        vector store metadata payload, reconstructing typed MemoryEntry and
        MemorySearchResult objects on retrieval.
    """

    def __init__(self, vector_store: VectorStorePort) -> None:
        """Initialize the adapter with a concrete VectorStorePort instance.

        Args:
            vector_store: Underlying VectorStorePort implementation (e.g. PgVectorStoreAdapter).
        """
        self._vector_store = vector_store

    def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry into the underlying vector store.

        Args:
            entry: MemoryEntry record with embedding vector.

        Returns:
            Unique identifier of the stored memory.

        Raises:
            AiError: If embedding is missing or underlying store fails.
        """
        if entry.embedding is None:
            raise AiError(
                "Cannot store MemoryEntry into vector store without an embedding vector."
            )

        payload: dict[str, Any] = {
            "content": entry.content,
            "timestamp": entry.timestamp.isoformat(),
            **entry.metadata,
        }
        try:
            self._vector_store.upsert(
                vector_id=entry.id,
                embedding=entry.embedding,
                metadata=payload,
            )
            return entry.id
        except Exception as err:
            raise AiError(f"Vector store upsert failed: {err}") from err

    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[MemorySearchResult]:
        """Search underlying vector store for similar memories.

        Args:
            query_embedding: Floating-point query vector.
            limit: Maximum result count.
            min_score: Minimum similarity score cutoff.

        Returns:
            List of MemorySearchResult instances sorted by relevance descending.

        Raises:
            AiError: If vector search fails.
        """
        try:
            matches = self._vector_store.search(
                query_embedding=query_embedding,
                limit=limit,
            )
        except Exception as err:
            raise AiError(f"Vector store search failed: {err}") from err

        results: list[MemorySearchResult] = []
        for match in matches:
            meta = dict(match)
            score = float(meta.pop("_score", 1.0))
            if score < min_score:
                continue

            entry_id = str(meta.pop("_id", ""))
            content = str(meta.pop("content", ""))
            raw_ts = meta.pop("timestamp", None)
            ts = datetime.fromisoformat(raw_ts) if raw_ts else datetime.now(UTC)

            entry = MemoryEntry(
                id=entry_id,
                content=content,
                embedding=None,
                metadata=meta,
                timestamp=ts,
            )
            results.append(MemorySearchResult(entry=entry, score=score))

        return results

    def get(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry by ID from the underlying vector store.

        Args:
            memory_id: Unique memory ID.

        Returns:
            MemoryEntry if supported and found, else None.
        """
        getter = getattr(self._vector_store, "get", None)
        if callable(getter):
            res = getter(memory_id)
            if res is None:
                return None
            emb, meta = res
            meta_copy = dict(meta)
            content = str(meta_copy.pop("content", ""))
            raw_ts = meta_copy.pop("timestamp", None)
            ts = datetime.fromisoformat(raw_ts) if raw_ts else datetime.now(UTC)
            return MemoryEntry(
                id=memory_id,
                content=content,
                embedding=list(emb),
                metadata=meta_copy,
                timestamp=ts,
            )
        return None

    def delete(self, memory_id: str) -> bool:
        """Delete a memory entry by ID from the underlying vector store.

        Args:
            memory_id: Unique memory ID.

        Returns:
            True if deleted, False otherwise.
        """
        deleter = getattr(self._vector_store, "delete", None)
        if callable(deleter):
            return bool(deleter(memory_id))
        return False

    def clear(self) -> None:
        """Clear all stored entries if supported by the underlying vector store."""
        clearer = getattr(self._vector_store, "clear", None)
        if callable(clearer):
            clearer()


__all__ = [
    "PgVectorMemoryAdapter",
]
