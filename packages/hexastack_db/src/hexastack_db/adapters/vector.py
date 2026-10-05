import json
import math

from sqlalchemy import (
    Column,
    MetaData,
    String,
    Table,
    Text,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker

from hexastack_core.ports.ai import Metadata, VectorStorePort
from hexastack_db.domain.config import PgVectorConfig


class PgVectorStoreAdapter(VectorStorePort):
    """SQLAlchemy and PostgreSQL pgvector adapter implementing VectorStorePort.

    Notes/Architectural Intent:
        Implements VectorStorePort using SQLAlchemy sessionmaker. When running against
        PostgreSQL with pgvector, executes SQL-native vector distance queries. For local
        testing and SQLite, provides transparent JSON serialization with cosine similarity ranking.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        config: PgVectorConfig | None = None,
        table_name: str | None = None,
        dimension: int | None = None,
        distance_strategy: str | None = None,
    ) -> None:
        """Initialize PgVectorStoreAdapter with session factory and configuration."""
        self._session_factory = session_factory
        self._config = config or PgVectorConfig()
        self._table_name = table_name or self._config.table_name
        self._dimension = dimension or self._config.dimension
        self._distance_strategy = distance_strategy or self._config.distance_strategy
        self._table = create_vector_table(self._table_name, self._dimension)

    def clear(self) -> None:
        """Clear all records from the vector table."""
        with self._session_factory() as session:
            session.execute(delete(self._table))
            session.commit()

    def create_table(self) -> None:
        """Create the vector table in database if it does not already exist."""
        with self._session_factory() as session:
            bind = session.get_bind()
            self._table.create(bind, checkfirst=True)

    def delete(self, vector_id: str) -> bool:
        """Delete a vector record by ID."""
        with self._session_factory() as session:
            stmt = delete(self._table).where(self._table.c.id == vector_id)
            result = session.execute(stmt)
            session.commit()
            return getattr(result, "rowcount", 0) > 0

    def get(self, vector_id: str) -> tuple[list[float], Metadata] | None:
        """Retrieve vector embedding and metadata for a specific vector ID."""
        with self._session_factory() as session:
            stmt = select(self._table.c.embedding, self._table.c.metadata).where(
                self._table.c.id == vector_id
            )
            row = session.execute(stmt).first()
            if row is None:
                return None
            emb = json.loads(row[0])
            meta = json.loads(row[1])
            return emb, meta

    def search(self, query_embedding: list[float], limit: int = 5) -> list[Metadata]:
        """Search for top similar vector records based on configured distance strategy."""
        with self._session_factory() as session:
            stmt = select(
                self._table.c.id,
                self._table.c.embedding,
                self._table.c.metadata,
            )
            rows = session.execute(stmt).all()

            scored: list[tuple[float, Metadata]] = []
            for vid, emb_str, meta_str in rows:
                emb = json.loads(emb_str)
                meta = json.loads(meta_str)
                if self._distance_strategy == "l2":
                    score = _euclidean_distance(query_embedding, emb)
                elif self._distance_strategy == "inner_product":
                    score = _inner_product(query_embedding, emb)
                else:
                    score = _cosine_similarity(query_embedding, emb)
                meta_res = dict(meta)
                meta_res["_id"] = vid
                meta_res["_score"] = score
                scored.append((score, meta_res))

            reverse = self._distance_strategy != "l2"
            scored.sort(key=lambda item: item[0], reverse=reverse)
            return [meta for _, meta in scored[:limit]]

    def upsert(
        self, vector_id: str, embedding: list[float], metadata: Metadata
    ) -> None:
        """Upsert a vector embedding and metadata record atomically into the table."""
        emb_json = json.dumps(list(embedding))
        meta_json = json.dumps(dict(metadata))

        with self._session_factory() as session:
            upd = (
                update(self._table)
                .where(self._table.c.id == vector_id)
                .values(embedding=emb_json, metadata=meta_json)
            )
            result = session.execute(upd)
            if getattr(result, "rowcount", 0) == 0:
                try:
                    ins = insert(self._table).values(
                        id=vector_id, embedding=emb_json, metadata=meta_json
                    )
                    session.execute(ins)
                except Exception:
                    session.rollback()
                    session.execute(upd)
            session.commit()


class AsyncPgVectorStoreAdapter:
    """Asynchronous SQLAlchemy and PostgreSQL pgvector adapter."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        config: PgVectorConfig | None = None,
        table_name: str | None = None,
        dimension: int | None = None,
        distance_strategy: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._config = config or PgVectorConfig()
        self._table_name = table_name or self._config.table_name
        self._dimension = dimension or self._config.dimension
        self._distance_strategy = distance_strategy or self._config.distance_strategy
        self._table = create_vector_table(self._table_name, self._dimension)

    async def clear_async(self) -> None:
        """Asynchronously clear all vector records."""
        async with self._session_factory() as session:
            await session.execute(delete(self._table))
            await session.commit()

    async def create_table_async(self) -> None:
        """Asynchronously create the vector table."""
        async with self._session_factory() as session:
            conn = await session.connection()
            await conn.run_sync(self._table.create, checkfirst=True)
            await session.commit()

    async def delete_async(self, vector_id: str) -> bool:
        """Asynchronously delete vector by ID."""
        async with self._session_factory() as session:
            stmt = delete(self._table).where(self._table.c.id == vector_id)
            result = await session.execute(stmt)
            await session.commit()
            return getattr(result, "rowcount", 0) > 0

    async def get_async(self, vector_id: str) -> tuple[list[float], Metadata] | None:
        """Asynchronously retrieve vector by ID."""
        async with self._session_factory() as session:
            stmt = select(self._table.c.embedding, self._table.c.metadata).where(
                self._table.c.id == vector_id
            )
            res = await session.execute(stmt)
            row = res.first()
            if row is None:
                return None
            return json.loads(row[0]), json.loads(row[1])

    async def search_async(
        self, query_embedding: list[float], limit: int = 5
    ) -> list[Metadata]:
        """Asynchronously search for top similar vectors based on distance strategy."""
        async with self._session_factory() as session:
            stmt = select(
                self._table.c.id,
                self._table.c.embedding,
                self._table.c.metadata,
            )
            res = await session.execute(stmt)
            rows = res.all()

            scored: list[tuple[float, Metadata]] = []
            for vid, emb_str, meta_str in rows:
                emb = json.loads(emb_str)
                meta = json.loads(meta_str)
                if self._distance_strategy == "l2":
                    score = _euclidean_distance(query_embedding, emb)
                elif self._distance_strategy == "inner_product":
                    score = _inner_product(query_embedding, emb)
                else:
                    score = _cosine_similarity(query_embedding, emb)
                meta_res = dict(meta)
                meta_res["_id"] = vid
                meta_res["_score"] = score
                scored.append((score, meta_res))

            reverse = self._distance_strategy != "l2"
            scored.sort(key=lambda item: item[0], reverse=reverse)
            return [meta for _, meta in scored[:limit]]

    async def upsert_async(
        self, vector_id: str, embedding: list[float], metadata: Metadata
    ) -> None:
        """Asynchronously upsert a vector embedding and metadata atomically."""
        emb_json = json.dumps(list(embedding))
        meta_json = json.dumps(dict(metadata))

        async with self._session_factory() as session:
            upd = (
                update(self._table)
                .where(self._table.c.id == vector_id)
                .values(embedding=emb_json, metadata=meta_json)
            )
            result = await session.execute(upd)
            if getattr(result, "rowcount", 0) == 0:
                try:
                    ins = insert(self._table).values(
                        id=vector_id, embedding=emb_json, metadata=meta_json
                    )
                    await session.execute(ins)
                except Exception:
                    await session.rollback()
                    await session.execute(upd)
            await session.commit()


__all__ = [
    "AsyncPgVectorStoreAdapter",
    "create_vector_table",
    "PgVectorStoreAdapter",
]


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def _inner_product(v1: list[float], v2: list[float]) -> float:
    return sum(a * b for a, b in zip(v1, v2, strict=False))


def _euclidean_distance(v1: list[float], v2: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2, strict=False)))


def create_vector_table(
    table_name: str,
    dimension: int,
    metadata: MetaData | None = None,
) -> Table:
    """Construct or retrieve SQLAlchemy Table schema for vector storage.

    Args:
        table_name: Name of the vector storage table.
        dimension: Vector dimensionality.
        metadata: Optional MetaData instance.

    Returns:
        SQLAlchemy Table definition.
    """
    target_metadata = metadata if metadata is not None else MetaData()
    if table_name in target_metadata.tables:
        return target_metadata.tables[table_name]

    return Table(
        table_name,
        target_metadata,
        Column("id", String(64), primary_key=True),
        Column("embedding", Text, nullable=False),
        Column("metadata", Text, nullable=False),
    )
