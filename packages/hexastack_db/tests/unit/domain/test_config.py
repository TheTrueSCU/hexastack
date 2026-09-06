from hexastack_db.domain.config import (
    HexastackDatabaseConfig,
    HexastackDbConfig,
    PgVectorConfig,
    PostgresDialectConfig,
    SqliteDialectConfig,
)


def test_hexastack_db_config_defaults():
    cfg = HexastackDatabaseConfig()
    assert cfg.url == "sqlite:///hexastack.db"
    assert cfg.echo is False
    assert cfg.pool_size == 5
    assert cfg.max_overflow == 10
    assert cfg.pool_timeout == 30
    assert cfg.pool_recycle == 1800
    assert cfg.auto_create_tables is False
    assert cfg.async_mode is False
    assert cfg.is_sqlite is True
    assert cfg.is_postgres is False
    assert isinstance(cfg.sqlite, SqliteDialectConfig)
    assert isinstance(cfg.postgres, PostgresDialectConfig)
    assert isinstance(cfg.vector, PgVectorConfig)
    assert HexastackDbConfig is HexastackDatabaseConfig

    # Test Postgres URL detection
    pg_cfg = HexastackDatabaseConfig(
        url="postgresql+asyncpg://user:pass@localhost:5432/mydb"  # pragma: allowlist secret
    )
    assert pg_cfg.is_postgres is True
    assert pg_cfg.is_sqlite is False


def test_sqlite_dialect_config_defaults():
    sqlite = SqliteDialectConfig()
    assert sqlite.foreign_keys is True
    assert sqlite.journal_mode == "WAL"
    assert sqlite.busy_timeout_ms == 5000
    assert sqlite.synchronous == "NORMAL"


def test_postgres_dialect_config_defaults():
    pg = PostgresDialectConfig()
    assert pg.search_path is None
    assert pg.ssl_mode is None
    assert pg.server_side_cursors is False

    custom_pg = PostgresDialectConfig(
        search_path="public,tenant",
        ssl_mode="require",
        server_side_cursors=True,
    )
    assert custom_pg.search_path == "public,tenant"
    assert custom_pg.ssl_mode == "require"
    assert custom_pg.server_side_cursors is True


def test_pg_vector_config_defaults():
    vec = PgVectorConfig()
    assert vec.enabled is False
    assert vec.table_name == "hexastack_vectors"
    assert vec.dimension == 1536
    assert vec.distance_strategy == "cosine"
    assert vec.index_type == "hnsw"
    assert vec.m == 16
    assert vec.ef_construction == 64
