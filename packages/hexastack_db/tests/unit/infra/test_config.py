from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_db.infra.config import (
    HexastackDatabaseConfig,
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


def test_database_config_postgres():
    config = HexastackDatabaseConfig(
        url="postgresql+asyncpg://user:pass@localhost:5432/mydb",
        echo=True,
        pool_size=10,
        async_mode=True,
    )
    assert config.is_sqlite is False
    assert config.is_postgres is True
    assert config.echo is True
    assert config.async_mode is True


def test_register_database_config():
    registry = ConfigRegistry()
    register_database_config(registry)
    assert "database" in registry
    assert registry.get("database") is HexastackDatabaseConfig
