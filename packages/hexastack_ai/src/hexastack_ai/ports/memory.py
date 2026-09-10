"""Abstract ports for vector memory storage and semantic query caching.

Notes/Architectural Intent:
    Defines abstract interfaces for storing, querying, and deleting high-dimensional
    vector memories, as well as semantic caching interfaces for LLM inference
    and CQRS query pipelines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hexastack_ai.domain.memory import MemoryEntry, MemorySearchResult


class VectorMemoryPort(ABC):
    """Abstract interface for synchronous vector memory storage and retrieval.

    Notes/Architectural Intent:
        Decouples application agents and domain services from concrete vector databases
        such as Qdrant, Milvus, Chroma, or pgvector.
    """

    @abstractmethod
    def store(self, entry: MemoryEntry) -> str:
        """Persist a memory entry and return its unique identifier.

        Args:
            entry: The memory entry to store.

        Returns:
            The unique identifier string of the stored memory.

        Raises:
            AiError: If persisting the memory entry fails.
        """

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[MemorySearchResult]:
        """Search stored memories by embedding cosine similarity.

        Args:
            query_embedding: Floating-point embedding vector of the search query.
            limit: Maximum number of ranked results to return.
            min_score: Minimum similarity score threshold (0.0 to 1.0).

        Returns:
            List of MemorySearchResult instances sorted by relevance descending.

        Raises:
            AiError: If executing the vector search fails.
        """

    @abstractmethod
    def get(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve a specific memory entry by its unique identifier.

        Args:
            memory_id: The unique identifier of the memory entry.

        Returns:
            The MemoryEntry if found, or None if not present.

        Raises:
            AiError: If retrieval fails unexpectedly.
        """

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete a specific memory entry by its unique identifier.

        Args:
            memory_id: The unique identifier of the memory entry to remove.

        Returns:
            True if the record was successfully deleted, False if it was not found.

        Raises:
            AiError: If deletion fails unexpectedly.
        """

    @abstractmethod
    def clear(self) -> None:
        """Delete all stored memories from the collection.

        Returns:
            None.

        Raises:
            AiError: If clearing the store fails.
        """


class AsyncVectorMemoryPort(ABC):
    """Abstract interface for asynchronous vector memory storage and retrieval.

    Notes/Architectural Intent:
        Asynchronous counterpart to VectorMemoryPort, designed for non-blocking
        I/O in FastAPI endpoints and async agent loops.
    """

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> str:
        """Persist a memory entry asynchronously and return its unique identifier.

        Args:
            entry: The memory entry to store.

        Returns:
            The unique identifier string of the stored memory.

        Raises:
            AiError: If persisting the memory entry fails.
        """

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[MemorySearchResult]:
        """Search stored memories asynchronously by embedding cosine similarity.

        Args:
            query_embedding: Floating-point embedding vector of the search query.
            limit: Maximum number of ranked results to return.
            min_score: Minimum similarity score threshold (0.0 to 1.0).

        Returns:
            List of MemorySearchResult instances sorted by relevance descending.

        Raises:
            AiError: If executing the vector search fails.
        """

    @abstractmethod
    async def get(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve a specific memory entry asynchronously by its unique identifier.

        Args:
            memory_id: The unique identifier of the memory entry.

        Returns:
            The MemoryEntry if found, or None if not present.

        Raises:
            AiError: If retrieval fails unexpectedly.
        """

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete a specific memory entry asynchronously by its unique identifier.

        Args:
            memory_id: The unique identifier of the memory entry to remove.

        Returns:
            True if the record was successfully deleted, False if it was not found.

        Raises:
            AiError: If deletion fails unexpectedly.
        """

    @abstractmethod
    async def clear(self) -> None:
        """Delete all stored memories asynchronously from the collection.

        Returns:
            None.

        Raises:
            AiError: If clearing the store fails.
        """


class SemanticCachePort(ABC):
    """Abstract interface for synchronous semantic query result caching.

    Notes/Architectural Intent:
        Allows domain pipelines to retrieve cached inference results or query payloads
        based on high vector similarity rather than exact string hashing.
    """

    @abstractmethod
    def get(
        self,
        query_embedding: list[float],
        threshold: float | None = None,
    ) -> Any | None:
        """Look up a cached result matching the query embedding within threshold.

        Args:
            query_embedding: Floating-point embedding vector of the input query.
            threshold: Optional override for the cosine similarity cutoff.

        Returns:
            The cached payload object if a match meets the threshold, else None.

        Raises:
            AiError: If cache query fails.
        """

    @abstractmethod
    def set(
        self,
        query_embedding: list[float],
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a result payload indexed by its query embedding.

        Args:
            query_embedding: Floating-point embedding vector of the input query.
            value: Arbitrary result payload to cache.
            ttl_seconds: Optional duration before this cached entry expires.

        Returns:
            None.

        Raises:
            AiError: If cache write fails.
        """

    @abstractmethod
    def clear(self) -> None:
        """Evict all cached entries from the semantic cache.

        Returns:
            None.

        Raises:
            AiError: If clearing cache fails.
        """


class AsyncSemanticCachePort(ABC):
    """Abstract interface for asynchronous semantic query result caching.

    Notes/Architectural Intent:
        Asynchronous variant of SemanticCachePort for non-blocking async pipeline caching.
    """

    @abstractmethod
    async def get(
        self,
        query_embedding: list[float],
        threshold: float | None = None,
    ) -> Any | None:
        """Look up a cached result asynchronously matching the query embedding.

        Args:
            query_embedding: Floating-point embedding vector of the input query.
            threshold: Optional override for the cosine similarity cutoff.

        Returns:
            The cached payload object if a match meets the threshold, else None.

        Raises:
            AiError: If cache query fails.
        """

    @abstractmethod
    async def set(
        self,
        query_embedding: list[float],
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a result payload asynchronously indexed by its query embedding.

        Args:
            query_embedding: Floating-point embedding vector of the input query.
            value: Arbitrary result payload to cache.
            ttl_seconds: Optional duration before this cached entry expires.

        Returns:
            None.

        Raises:
            AiError: If cache write fails.
        """

    @abstractmethod
    async def clear(self) -> None:
        """Evict all cached entries asynchronously from the semantic cache.

        Returns:
            None.

        Raises:
            AiError: If clearing cache fails.
        """


__all__ = [
    "AsyncSemanticCachePort",
    "AsyncVectorMemoryPort",
    "SemanticCachePort",
    "VectorMemoryPort",
]
