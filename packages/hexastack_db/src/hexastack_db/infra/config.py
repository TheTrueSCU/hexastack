from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_db.domain.config import (
    HexastackDatabaseConfig,
    HexastackDbConfig,
    PgVectorConfig,
    PostgresDialectConfig,
    SqliteDialectConfig,
)

config_section("db")(HexastackDatabaseConfig)

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
