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
    assert cfg.is_sqlite is True
    assert cfg.is_postgres is False
    assert isinstance(cfg.sqlite, SqliteDialectConfig)
    assert isinstance(cfg.postgres, PostgresDialectConfig)
    assert isinstance(cfg.vector, PgVectorConfig)
    assert HexastackDbConfig is HexastackDatabaseConfig
