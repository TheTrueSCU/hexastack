from typing import Literal

from pydantic import BaseModel, Field

from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry


class SqliteDialectConfig(BaseModel):
    """Configuration options specific to SQLite database connections.

    Notes/Architectural Intent:
        Encapsulates SQLite-specific PRAGMA settings and connection tuning
        decoupled from generic connection pooling.
    """

    foreign_keys: bool = Field(
        default=True,
        description="Enforce SQLite foreign key constraints via 'PRAGMA foreign_keys = ON'.",
    )
    journal_mode: str = Field(
        default="WAL",
        description="SQLite journal mode (e.g. 'WAL', 'DELETE', 'MEMORY').",
    )
    busy_timeout_ms: int = Field(
        default=5000,
        description="SQLite busy timeout in milliseconds to prevent database locked errors.",
    )
    synchronous: str = Field(
        default="NORMAL",
        description="SQLite synchronous mode ('NORMAL', 'FULL', 'OFF').",
    )


class PostgresDialectConfig(BaseModel):
    """Configuration options specific to PostgreSQL database connections.

    Notes/Architectural Intent:
        Encapsulates PostgreSQL-specific connection parameters and schemas.
    """

    search_path: str | None = Field(
        default=None,
        description="PostgreSQL schema search path (e.g. 'public, custom_schema').",
    )
    ssl_mode: str | None = Field(
        default=None,
        description="PostgreSQL SSL mode (e.g. 'require', 'verify-full', 'disable').",
    )
    server_side_cursors: bool = Field(
        default=False,
        description="Enable server-side streaming cursors for large query result sets.",
    )


class PgVectorConfig(BaseModel):
    """Configuration options for PostgreSQL pgvector storage and indexing.

    Notes/Architectural Intent:
        Configures table schema, vector dimensionality, and distance metrics for
        VectorStorePort implementations backed by pgvector.
    """

    enabled: bool = Field(
        default=False,
        description="Enable automatic VectorStorePort registration backed by pgvector.",
    )
    table_name: str = Field(
        default="hexastack_vectors",
        description="Table name used for storing vector embeddings and metadata.",
    )
    dimension: int = Field(
        default=1536,
        description="Embedding vector dimensionality (e.g. 1536 for OpenAI, 768 for Gemini/Bert).",
    )
    distance_strategy: Literal["cosine", "l2", "inner_product"] = Field(
        default="cosine",
        description="Distance operator used for similarity searches ('cosine', 'l2', 'inner_product').",
    )
    index_type: Literal["hnsw", "ivfflat", "none"] = Field(
        default="hnsw",
        description="Vector index type to generate ('hnsw', 'ivfflat', 'none').",
    )
    m: int = Field(
        default=16,
        description="HNSW max number of bidirectional links per vector node.",
    )
    ef_construction: int = Field(
        default=64,
        description="HNSW size of the dynamic candidate list for index building.",
    )


@config_section("db")
class HexastackDatabaseConfig(BaseModel):
    """Configuration schema for Hexastack SQLAlchemy database adapter under 'db'.

    Notes/Architectural Intent:
        Separates global database pooling and execution settings from dialect-specific
        subsections (SQLite, PostgreSQL, pgvector) mapped to TOML section [hexastack.db].
    """

    # Global Settings
    url: str = Field(
        default="sqlite:///hexastack.db",
        description="SQLAlchemy database connection URL (e.g. sqlite:///db.sqlite or postgresql+asyncpg://...)",
    )
    echo: bool = Field(
        default=False,
        description="Enable raw SQLAlchemy SQL statement logging.",
    )
    pool_size: int = Field(
        default=5,
        description="Number of connections maintained in the connection pool.",
    )
    max_overflow: int = Field(
        default=10,
        description="Maximum temporary connections allowed beyond pool_size.",
    )
    pool_timeout: int = Field(
        default=30,
        description="Timeout in seconds when waiting for a connection from pool.",
    )
    pool_recycle: int = Field(
        default=1800,
        description="Connection recycle duration in seconds to prevent stale connections.",
    )
    auto_create_tables: bool = Field(
        default=False,
        description="Automatically create tables from declarative metadata upon bootstrap.",
    )
    async_mode: bool = Field(
        default=False,
        description="Enable asynchronous SQLAlchemy engine and sessions.",
    )

    # Dialect-Specific Subsections
    sqlite: SqliteDialectConfig = Field(
        default_factory=SqliteDialectConfig,
        description="SQLite-specific dialect settings and PRAGMAs.",
    )
    postgres: PostgresDialectConfig = Field(
        default_factory=PostgresDialectConfig,
        description="PostgreSQL-specific dialect settings and schemas.",
    )
    vector: PgVectorConfig = Field(
        default_factory=PgVectorConfig,
        description="PostgreSQL pgvector storage and indexing configuration.",
    )

    @property
    def is_postgres(self) -> bool:
        """Return True if connection URL targets a PostgreSQL database."""
        return "postgres" in self.url.lower()

    @property
    def is_sqlite(self) -> bool:
        """Return True if connection URL targets an SQLite database."""
        return "sqlite" in self.url.lower()


# Alias for backward compatibility / natural naming
HexastackDbConfig = HexastackDatabaseConfig


__all__ = [
    "HexastackDatabaseConfig",
    "HexastackDbConfig",
    "PgVectorConfig",
    "PostgresDialectConfig",
    "register_database_config",
    "SqliteDialectConfig",
]


def register_database_config(registry: ConfigRegistry) -> None:
    """Register database configuration schema under 'db'.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("db", HexastackDatabaseConfig)
