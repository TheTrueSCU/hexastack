from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_db.infra.config import (
    HexastackDatabaseConfig,
    PgVectorConfig,
    PostgresDialectConfig,
    SqliteDialectConfig,
    register_database_config,
)


def test_database_config_defaults():
    config = HexastackDatabaseConfig()
    assert "sqlite" in config.url
    assert config.is_sqlite is True
    assert config.is_postgres is False
    assert config.pool_size == 5
    assert config.echo is False
    assert config.async_mode is False

    # Dialect defaults
    assert config.sqlite.foreign_keys is True
    assert config.sqlite.journal_mode == "WAL"
    assert config.sqlite.busy_timeout_ms == 5000
    assert config.postgres.search_path is None
    assert config.vector.enabled is False
    assert config.vector.table_name == "hexastack_vectors"
    assert config.vector.dimension == 1536


def test_database_config_custom_dialect_sections():
    config = HexastackDatabaseConfig(
        url="postgresql+asyncpg://user:pass@localhost:5432/mydb",
        echo=True,
        pool_size=10,
        async_mode=True,
        sqlite=SqliteDialectConfig(foreign_keys=False, journal_mode="DELETE"),
        postgres=PostgresDialectConfig(search_path="custom_schema", ssl_mode="require"),
        vector=PgVectorConfig(enabled=True, table_name="documents_vec", dimension=768),
    )
    assert config.is_sqlite is False
    assert config.is_postgres is True
    assert config.echo is True
    assert config.async_mode is True
    assert config.sqlite.foreign_keys is False
    assert config.postgres.search_path == "custom_schema"
    assert config.postgres.ssl_mode == "require"
    assert config.vector.enabled is True
    assert config.vector.table_name == "documents_vec"
    assert config.vector.dimension == 768


def test_register_database_config():
    registry = ConfigRegistry()
    register_database_config(registry)
    assert "db" in registry
    assert registry.get("db") is HexastackDatabaseConfig
