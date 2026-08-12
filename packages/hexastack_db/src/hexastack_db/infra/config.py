from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from pydantic import BaseModel, Field


@config_section("database")
class HexastackDatabaseConfig(BaseModel):
    """Configuration schema for Hexastack SQLAlchemy database adapter.

    Notes/Architectural Intent:
        Controls connection URLs, pooling, SQL logging, table creation, and async mode.
    """

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

    @property
    def is_sqlite(self) -> bool:
        """Return True if connection URL targets an SQLite database."""
        return "sqlite" in self.url.lower()

    @property
    def is_postgres(self) -> bool:
        """Return True if connection URL targets a PostgreSQL database."""
        return "postgres" in self.url.lower()


def register_database_config(registry: ConfigRegistry) -> None:
    """Register database configuration schema under 'database'.

    Args:
        registry: Target ConfigRegistry instance.

    Returns:
        None.

    Raises:
        None.
    """
    registry.register_config_section("database", HexastackDatabaseConfig)


__all__ = [
    "HexastackDatabaseConfig",
    "register_database_config",
]
