"""Qdrant vector database adapters for long-term agent memory storage.

Notes/Architectural Intent:
    Implements VectorMemoryPort and AsyncVectorMemoryPort using the official
    qdrant-client SDK. Uses lazy imports via require_dependency so hexastack-ai
    can load without qdrant-client installed, raising an actionable ImportError
    pointing to ``pip install hexastack-ai[qdrant]`` only when invoked.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from typing import Any

from hexastack_ai.domain.exceptions import AiError
from hexastack_ai.domain.memory import MemoryEntry, MemorySearchResult, QdrantConfig
from hexastack_ai.ports.memory import AsyncVectorMemoryPort, VectorMemoryPort
from hexastack_core.utils.imports import require_dependency


class QdrantVectorMemoryAdapter(VectorMemoryPort):
    """Qdrant-backed synchronous vector memory adapter.

    Notes/Architectural Intent:
        Communicates with in-memory, disk-embedded, or remote Qdrant instances.
        Auto-provisions collections if they do not yet exist, mapping MemoryEntry
        records to Qdrant PointStruct items with payload metadata.
    """

    def __init__(
        self,
        config: QdrantConfig | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        """Initialize synchronous Qdrant adapter with configuration and optional client override.

        Args:
            config: QdrantConfig connection parameters.
            client: Optional pre-configured synchronous QdrantClient instance.
        """
        self._config = config or QdrantConfig()
        self._client = client
        self._initialized = False

    def _get_client(self) -> Any:
        """Return lazily initialized synchronous QdrantClient."""
        if self._client is None:
            qc = require_dependency(
                "qdrant_client",
                extra="qdrant",
                package="hexastack-ai",
                feature_name="QdrantVectorMemoryAdapter",
            )
            if self._config.url:
                self._client = qc.QdrantClient(
                    url=self._config.url,
                    api_key=self._config.api_key,
                )
            elif self._config.path:
                self._client = qc.QdrantClient(path=self._config.path)
            else:
                self._client = qc.QdrantClient(
                    location=self._config.location or ":memory:"
                )
        self._ensure_collection_exists()
        return self._client

    def _ensure_collection_exists(self) -> None:
        """Verify collection exists in Qdrant; create if missing."""
        client = self._client
        if self._initialized or client is None:
            return

        require_dependency(
            "qdrant_client",
            extra="qdrant",
            package="hexastack-ai",
            feature_name="QdrantVectorMemoryAdapter",
        )
        from qdrant_client.http import models as qmodels

        distance_map = {
            "cosine": qmodels.Distance.COSINE,
            "euclid": qmodels.Distance.EUCLID,
            "dot": qmodels.Distance.DOT,
        }
        dist = distance_map.get(self._config.distance.lower(), qmodels.Distance.COSINE)

        try:
            if not client.collection_exists(self._config.collection_name):
                client.create_collection(
                    collection_name=self._config.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self._config.vector_size,
                        distance=dist,
                    ),
                )
            self._initialized = True
        except Exception as err:
            raise AiError(
                f"Failed to verify or create Qdrant collection: {err}"
            ) from err

    def store(self, entry: MemoryEntry) -> str:
        """Persist a memory entry into Qdrant collection.

        Args:
            entry: The memory entry to store.

        Returns:
            The unique identifier string of the stored memory.

        Raises:
            AiError: If upsert operation fails.
        """
        if entry.embedding is None:
            raise AiError("Cannot store MemoryEntry in Qdrant without an embedding.")

        client = self._get_client()
        from qdrant_client.http import models as qmodels

        payload = {
            "content": entry.content,
            "timestamp": entry.timestamp.isoformat(),
            **entry.metadata,
        }
        try:
            point = qmodels.PointStruct(
                id=entry.id,
                vector=entry.embedding,
                payload=payload,
            )
            client.upsert(
                collection_name=self._config.collection_name,
                points=[point],
            )
            return entry.id
        except Exception as err:
            raise AiError(f"Failed to upsert memory point to Qdrant: {err}") from err

    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[MemorySearchResult]:
        """Search Qdrant for nearest memory points matching query vector.

        Args:
            query_embedding: Floating-point query vector.
            limit: Maximum number of points to retrieve.
            min_score: Minimum cosine similarity score.

        Returns:
            List of MemorySearchResult instances sorted by relevance descending.

        Raises:
            AiError: If search execution fails.
        """
        client = self._get_client()
        try:
            if hasattr(client, "query_points"):
                response = client.query_points(
                    collection_name=self._config.collection_name,
                    query=query_embedding,
                    limit=limit,
                    score_threshold=min_score if min_score > 0.0 else None,
                    with_payload=True,
                    with_vectors=True,
                )
                points = getattr(response, "points", response)
            else:
                points = client.search(
                    collection_name=self._config.collection_name,
                    query_vector=query_embedding,
                    limit=limit,
                    score_threshold=min_score if min_score > 0.0 else None,
                    with_payload=True,
                    with_vectors=True,
                )
        except Exception as err:
            raise AiError(f"Qdrant vector search failed: {err}") from err

        results: list[MemorySearchResult] = []
        for pt in points:
            score = float(getattr(pt, "score", 0.0))
            payload = dict(getattr(pt, "payload", {}) or {})
            content = payload.pop("content", "")
            raw_ts = payload.pop("timestamp", None)
            ts = datetime.fromisoformat(raw_ts) if raw_ts else datetime.now(UTC)
            raw_vec = getattr(pt, "vector", None)
            vec = list(raw_vec) if raw_vec is not None else None

            entry = MemoryEntry(
                id=str(pt.id),
                content=content,
                embedding=vec,
                metadata=payload,
                timestamp=ts,
            )
            results.append(MemorySearchResult(entry=entry, score=score))

        return results

    def get(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve a specific memory entry by ID from Qdrant.

        Args:
            memory_id: Unique point ID string.

        Returns:
            MemoryEntry if located, else None.
        """
        client = self._get_client()
        try:
            points = client.retrieve(
                collection_name=self._config.collection_name,
                ids=[memory_id],
                with_payload=True,
                with_vectors=True,
            )
            if not points:
                return None
            pt = points[0]
            payload = dict(getattr(pt, "payload", {}) or {})
            content = payload.pop("content", "")
            raw_ts = payload.pop("timestamp", None)
            ts = datetime.fromisoformat(raw_ts) if raw_ts else datetime.now(UTC)
            raw_vec = getattr(pt, "vector", None)
            vec = list(raw_vec) if raw_vec is not None else None
            return MemoryEntry(
                id=str(pt.id),
                content=content,
                embedding=vec,
                metadata=payload,
                timestamp=ts,
            )
        except Exception as err:
            raise AiError(f"Failed to retrieve point from Qdrant: {err}") from err

    def delete(self, memory_id: str) -> bool:
        """Delete a memory point by ID from Qdrant.

        Args:
            memory_id: Unique point ID string.

        Returns:
            True if deleted successfully.
        """
        client = self._get_client()
        from qdrant_client.http import models as qmodels

        try:
            client.delete(
                collection_name=self._config.collection_name,
                points_selector=qmodels.PointIdsList(points=[memory_id]),
            )
            return True
        except Exception as err:
            raise AiError(f"Failed to delete point from Qdrant: {err}") from err

    def clear(self) -> None:
        """Clear all memory points by deleting and recreating the collection in Qdrant."""
        client = self._get_client()
        try:
            client.delete_collection(collection_name=self._config.collection_name)
            self._initialized = False
            self._ensure_collection_exists()
        except Exception as err:
            raise AiError(f"Failed to clear Qdrant collection: {err}") from err


class AsyncQdrantVectorMemoryAdapter(AsyncVectorMemoryPort):
    """Qdrant-backed asynchronous vector memory adapter.

    Notes/Architectural Intent:
        Asynchronous counterpart to QdrantVectorMemoryAdapter communicating via
        AsyncQdrantClient for non-blocking I/O in FastAPI or asynchronous agent loops.
    """

    def __init__(
        self,
        config: QdrantConfig | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        """Initialize asynchronous Qdrant adapter with configuration and optional client override.

        Args:
            config: QdrantConfig connection parameters.
            client: Optional pre-configured AsyncQdrantClient instance.
        """
        self._config = config or QdrantConfig()
        self._client = client
        self._initialized = False

    def _get_client(self) -> Any:
        """Return lazily initialized AsyncQdrantClient."""
        if self._client is None:
            qc = require_dependency(
                "qdrant_client",
                extra="qdrant",
                package="hexastack-ai",
                feature_name="AsyncQdrantVectorMemoryAdapter",
            )
            if self._config.url:
                self._client = qc.AsyncQdrantClient(
                    url=self._config.url,
                    api_key=self._config.api_key,
                )
            elif self._config.path:
                self._client = qc.AsyncQdrantClient(path=self._config.path)
            else:
                self._client = qc.AsyncQdrantClient(
                    location=self._config.location or ":memory:"
                )
        return self._client

    async def _ensure_collection_exists(self) -> None:
        """Asynchronously verify collection exists in Qdrant; create if missing."""
        if self._initialized:
            return

        require_dependency(
            "qdrant_client",
            extra="qdrant",
            package="hexastack-ai",
            feature_name="AsyncQdrantVectorMemoryAdapter",
        )
        from qdrant_client.http import models as qmodels

        distance_map = {
            "cosine": qmodels.Distance.COSINE,
            "euclid": qmodels.Distance.EUCLID,
            "dot": qmodels.Distance.DOT,
        }
        dist = distance_map.get(self._config.distance.lower(), qmodels.Distance.COSINE)

        client = self._get_client()
        try:
            exists_res = client.collection_exists(self._config.collection_name)
            if inspect.isawaitable(exists_res):
                exists = await exists_res
            else:
                exists = bool(exists_res)
            if not exists:
                create_res = client.create_collection(
                    collection_name=self._config.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self._config.vector_size,
                        distance=dist,
                    ),
                )
                if inspect.isawaitable(create_res):
                    await create_res
            self._initialized = True
        except Exception as err:
            raise AiError(
                f"Failed to verify or create async Qdrant collection: {err}"
            ) from err

    async def store(self, entry: MemoryEntry) -> str:
        """Persist a memory entry asynchronously into Qdrant collection.

        Args:
            entry: The memory entry to store.

        Returns:
            The unique identifier string of the stored memory.

        Raises:
            AiError: If upsert operation fails.
        """
        if entry.embedding is None:
            raise AiError("Cannot store MemoryEntry in Qdrant without an embedding.")

        await self._ensure_collection_exists()
        client = self._get_client()
        from qdrant_client.http import models as qmodels

        payload = {
            "content": entry.content,
            "timestamp": entry.timestamp.isoformat(),
            **entry.metadata,
        }
        try:
            point = qmodels.PointStruct(
                id=entry.id,
                vector=entry.embedding,
                payload=payload,
            )
            upsert_res = client.upsert(
                collection_name=self._config.collection_name,
                points=[point],
            )
            if inspect.isawaitable(upsert_res):
                await upsert_res
            return entry.id
        except Exception as err:
            raise AiError(
                f"Failed to async upsert memory point to Qdrant: {err}"
            ) from err

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[MemorySearchResult]:
        """Search Qdrant asynchronously for nearest memory points matching query vector.

        Args:
            query_embedding: Floating-point query vector.
            limit: Maximum number of points to retrieve.
            min_score: Minimum cosine similarity score.

        Returns:
            List of MemorySearchResult instances sorted by relevance descending.

        Raises:
            AiError: If search execution fails.
        """
        await self._ensure_collection_exists()
        client = self._get_client()
        try:
            if hasattr(client, "query_points"):
                resp = client.query_points(
                    collection_name=self._config.collection_name,
                    query=query_embedding,
                    limit=limit,
                    score_threshold=min_score if min_score > 0.0 else None,
                    with_payload=True,
                    with_vectors=True,
                )
                response = await resp if inspect.isawaitable(resp) else resp
                points = getattr(response, "points", response)
            else:
                resp = client.search(
                    collection_name=self._config.collection_name,
                    query_vector=query_embedding,
                    limit=limit,
                    score_threshold=min_score if min_score > 0.0 else None,
                    with_payload=True,
                    with_vectors=True,
                )
                points = await resp if inspect.isawaitable(resp) else resp
        except Exception as err:
            raise AiError(f"Async Qdrant vector search failed: {err}") from err

        results: list[MemorySearchResult] = []
        for pt in points:
            score = float(getattr(pt, "score", 0.0))
            payload = dict(getattr(pt, "payload", {}) or {})
            content = payload.pop("content", "")
            raw_ts = payload.pop("timestamp", None)
            ts = datetime.fromisoformat(raw_ts) if raw_ts else datetime.now(UTC)
            raw_vec = getattr(pt, "vector", None)
            vec = list(raw_vec) if raw_vec is not None else None

            entry = MemoryEntry(
                id=str(pt.id),
                content=content,
                embedding=vec,
                metadata=payload,
                timestamp=ts,
            )
            results.append(MemorySearchResult(entry=entry, score=score))

        return results

    async def get(self, memory_id: str) -> MemoryEntry | None:
        """Retrieve a specific memory entry by ID asynchronously from Qdrant.

        Args:
            memory_id: Unique point ID string.

        Returns:
            MemoryEntry if located, else None.
        """
        await self._ensure_collection_exists()
        client = self._get_client()
        try:
            pts = client.retrieve(
                collection_name=self._config.collection_name,
                ids=[memory_id],
                with_payload=True,
                with_vectors=True,
            )
            points = await pts if inspect.isawaitable(pts) else pts
            if not points:
                return None
            pt = points[0]
            payload = dict(getattr(pt, "payload", {}) or {})
            content = payload.pop("content", "")
            raw_ts = payload.pop("timestamp", None)
            ts = datetime.fromisoformat(raw_ts) if raw_ts else datetime.now(UTC)
            raw_vec = getattr(pt, "vector", None)
            vec = list(raw_vec) if raw_vec is not None else None
            return MemoryEntry(
                id=str(pt.id),
                content=content,
                embedding=vec,
                metadata=payload,
                timestamp=ts,
            )
        except Exception as err:
            raise AiError(f"Failed to async retrieve point from Qdrant: {err}") from err

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory point by ID asynchronously from Qdrant.

        Args:
            memory_id: Unique point ID string.

        Returns:
            True if deleted successfully.
        """
        await self._ensure_collection_exists()
        client = self._get_client()
        from qdrant_client.http import models as qmodels

        try:
            del_res = client.delete(
                collection_name=self._config.collection_name,
                points_selector=qmodels.PointIdsList(points=[memory_id]),
            )
            if inspect.isawaitable(del_res):
                await del_res
            return True
        except Exception as err:
            raise AiError(f"Failed to async delete point from Qdrant: {err}") from err

    async def clear(self) -> None:
        """Clear all memory points asynchronously in Qdrant."""
        await self._ensure_collection_exists()
        client = self._get_client()
        try:
            del_col_res = client.delete_collection(
                collection_name=self._config.collection_name
            )
            if inspect.isawaitable(del_col_res):
                await del_col_res
            self._initialized = False
            await self._ensure_collection_exists()
        except Exception as err:
            raise AiError(f"Failed to async clear Qdrant collection: {err}") from err


__all__ = [
    "AsyncQdrantVectorMemoryAdapter",
    "QdrantVectorMemoryAdapter",
]
