"""Domain models for AI agent long-term vector memory and semantic caching.

Notes/Architectural Intent:
    Defines immutable data models representing vector memories, search results,
    and cache configurations independently of any specific vector database or
    embedding provider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """Represents a discrete memory item stored with an optional vector embedding.

    Notes/Architectural Intent:
        Encapsulates unstructured textual knowledge or conversational history
        alongside structured metadata and high-dimensional embeddings for similarity
        retrieval.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str = Field(description="Raw text content or conversational message.")
    embedding: list[float] | None = Field(
        default=None,
        description="High-dimensional floating point embedding vector.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary structured metadata tags associated with the memory.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the memory record was produced.",
    )


class MemorySearchResult(BaseModel):
    """Result item returned by a vector memory similarity query.

    Notes/Architectural Intent:
        Pairs the underlying MemoryEntry entity with its similarity or distance score
        computed by the vector index.
    """

    entry: MemoryEntry = Field(description="Retrieved memory record.")
    score: float = Field(
        description="Relevance or cosine similarity score (typically between 0.0 and 1.0)."
    )


class SemanticCacheConfig(BaseModel):
    """Configuration settings for semantic query and inference caching.

    Notes/Architectural Intent:
        Governs the threshold at which two query vectors are considered semantically
        equivalent, along with TTL expiry and maximum memory entry counts.
    """

    similarity_threshold: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity required to trigger a cache hit.",
    )
    ttl_seconds: int = Field(
        default=3600,
        ge=0,
        description="Time-to-live in seconds for cached semantic entries (0 = never expires).",
    )
    max_entries: int = Field(
        default=1000,
        gt=0,
        description="Maximum capacity of the semantic cache before eviction.",
    )


class QdrantConfig(BaseModel):
    """Configuration parameters for connecting to a Qdrant vector database.

    Notes/Architectural Intent:
        Provides structured connectivity settings for local in-memory, disk-backed,
        or distributed Qdrant vector engine instances.
    """

    collection_name: str = Field(
        default="hexastack_memories",
        description="Target Qdrant collection name for storing memory points.",
    )
    vector_size: int = Field(
        default=1536,
        gt=0,
        description="Dimensionality of the embedding vectors.",
    )
    distance: str = Field(
        default="Cosine",
        description="Vector distance metric: 'Cosine', 'Euclid', or 'Dot'.",
    )
    url: str | None = Field(
        default=None,
        description="Remote Qdrant server URL (e.g. http://localhost:6333).",
    )
    api_key: str | None = Field(
        default=None,
        description="Optional API authorization key for Qdrant Cloud or protected clusters.",
    )
    path: str | None = Field(
        default=None,
        description="Local directory path for embedded on-disk Qdrant storage.",
    )
    location: str | None = Field(
        default=":memory:",
        description="Qdrant location identifier (e.g. ':memory:' for ephemeral in-memory execution).",
    )


__all__ = [
    "MemoryEntry",
    "MemorySearchResult",
    "QdrantConfig",
    "SemanticCacheConfig",
]
