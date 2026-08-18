from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_db.infra.config import (
    HexastackDatabaseConfig,
    HexastackDbConfig,
    PgVectorConfig,
    PostgresDialectConfig,
    SqliteDialectConfig,
    register_database_config,
)


def test_database_config_custom_dialect_sections():
    config = HexastackDatabaseConfig(
        url="postgresql+asyncpg://user:pass@localhost:5432/mydb",
        echo=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=60,
        pool_recycle=3600,
        auto_create_tables=True,
        async_mode=True,
        sqlite=SqliteDialectConfig(
            foreign_keys=False,
            journal_mode="DELETE",
            busy_timeout_ms=10000,
            synchronous="FULL",
        ),
        postgres=PostgresDialectConfig(
            search_path="custom_schema",
            ssl_mode="require",
            server_side_cursors=True,
        ),
        vector=PgVectorConfig(
            enabled=True,
            table_name="documents_vec",
            dimension=768,
            distance_strategy="l2",
            index_type="ivfflat",
            m=32,
            ef_construction=128,
        ),
    )
    assert config.is_sqlite is False
    assert config.is_postgres is True
    assert config.echo is True
    assert config.pool_size == 10
    assert config.max_overflow == 20
    assert config.pool_timeout == 60
    assert config.pool_recycle == 3600
    assert config.auto_create_tables is True
    assert config.async_mode is True

    assert config.sqlite.foreign_keys is False
    assert config.sqlite.journal_mode == "DELETE"
    assert config.sqlite.busy_timeout_ms == 10000
    assert config.sqlite.synchronous == "FULL"

    assert config.postgres.search_path == "custom_schema"
    assert config.postgres.ssl_mode == "require"
    assert config.postgres.server_side_cursors is True

    assert config.vector.enabled is True
    assert config.vector.table_name == "documents_vec"
    assert config.vector.dimension == 768
    assert config.vector.distance_strategy == "l2"
    assert config.vector.index_type == "ivfflat"
    assert config.vector.m == 32
    assert config.vector.ef_construction == 128


def test_database_config_defaults():
    config = HexastackDatabaseConfig()
    assert config.url == "sqlite:///hexastack.db"
    assert config.is_sqlite is True
    assert config.is_postgres is False
    assert config.pool_size == 5
    assert config.max_overflow == 10
    assert config.pool_timeout == 30
    assert config.pool_recycle == 1800
    assert config.auto_create_tables is False
    assert config.echo is False
    assert config.async_mode is False

    # Dialect defaults
    assert config.sqlite.foreign_keys is True
    assert config.sqlite.journal_mode == "WAL"
    assert config.sqlite.busy_timeout_ms == 5000
    assert config.sqlite.synchronous == "NORMAL"

    assert config.postgres.search_path is None
    assert config.postgres.ssl_mode is None
    assert config.postgres.server_side_cursors is False

    assert config.vector.enabled is False
    assert config.vector.table_name == "hexastack_vectors"
    assert config.vector.dimension == 1536
    assert config.vector.distance_strategy == "cosine"
    assert config.vector.index_type == "hnsw"
    assert config.vector.m == 16
    assert config.vector.ef_construction == 64

    assert HexastackDbConfig is HexastackDatabaseConfig


def test_register_database_config():
    registry = ConfigRegistry()
    register_database_config(registry)
    assert "db" in registry
    assert registry.get("db") is HexastackDatabaseConfig
