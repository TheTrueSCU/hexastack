from dataclasses import dataclass
from typing import Any

from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_core.ports.unit_of_work import UnitOfWorkPort
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import Session, sessionmaker

from hexastack_db.adapters.unit_of_work import (
    AsyncSqlAlchemyUnitOfWork,
    SqlAlchemyUnitOfWork,
)
from hexastack_db.infra.config import (
    HexastackDatabaseConfig,
    register_database_config,
)
from hexastack_db.infra.engine import (
    create_async_db_engine,
    create_async_session_factory,
    create_db_engine,
    create_session_factory,
)
from hexastack_db.infra.registries.metadata import get_registered_metadata


@dataclass(frozen=True)
class DatabaseBootstrapResult:
    """Dataclass holding initialized database engines, sessionmakers, and Unit of Work."""

    config: HexastackDatabaseConfig
    engine: Engine | AsyncEngine
    session_factory: sessionmaker[Session] | async_sessionmaker[AsyncSession]
    uow: SqlAlchemyUnitOfWork | AsyncSqlAlchemyUnitOfWork


class DatabaseBootstrapper(BootstrapperPort):
    """Bootstrap extension initializing SQLAlchemy engines, sessions, and UnitOfWork.

    Notes/Architectural Intent:
        Implements BootstrapperPort with order=15 (executing before CQRS order=20),
        registering database configuration and injecting UnitOfWorkPort into DI.
        When auto_create_tables=True, runs create_all() on all metadata objects
        registered via register_metadata().
    """

    name: str = "database"
    order: int = 15

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Assemble database engine, sessionmaker, and UnitOfWork in DI container.

        Args:
            context: BootstrapContext containing DI container and config.

        Returns:
            None.

        Raises:
            None.
        """
        di = context.container

        # 1. Read Database Configuration
        db_config = context.get_config("database", HexastackDatabaseConfig)

        engine: Engine | AsyncEngine
        session_factory: Any
        uow: SqlAlchemyUnitOfWork | AsyncSqlAlchemyUnitOfWork

        # 2. Build Engine & Session Factory based on async_mode
        if db_config.async_mode:
            async_engine = create_async_db_engine(db_config)
            async_factory = create_async_session_factory(async_engine)
            async_uow = AsyncSqlAlchemyUnitOfWork(session_factory=async_factory)

            di.add_instance(async_engine, declared_class=AsyncEngine)
            di.add_instance(async_factory)
            di.add_instance(async_uow, declared_class=AsyncSqlAlchemyUnitOfWork)

            engine = async_engine
            session_factory = async_factory
            uow = async_uow
        else:
            sync_engine = create_db_engine(db_config)
            sync_factory = create_session_factory(sync_engine)
            sync_uow = SqlAlchemyUnitOfWork(session_factory=sync_factory)

            di.add_instance(sync_engine, declared_class=Engine)
            di.add_instance(sync_factory)
            di.add_instance(sync_uow, declared_class=UnitOfWorkPort)
            di.add_instance(sync_uow, declared_class=SqlAlchemyUnitOfWork)

            engine = sync_engine
            session_factory = sync_factory
            uow = sync_uow

        # 3. Run create_all on registered metadata if configured
        if db_config.auto_create_tables:
            registered = get_registered_metadata()
            if registered:
                if db_config.async_mode:
                    # Async engines require a sync-compatible connection for DDL;
                    # use the sync URL (strip async driver prefix) for create_all.
                    sync_url = (
                        str(engine.url)
                        .replace("+aiosqlite", "")
                        .replace("+asyncpg", "")
                    )
                    from sqlalchemy import create_engine as _ce
                    from sqlalchemy.pool import NullPool

                    _sync = _ce(sync_url, poolclass=NullPool)
                    for metadata in registered:
                        metadata.create_all(_sync)
                    _sync.dispose()
                else:
                    assert isinstance(engine, Engine)
                    for metadata in registered:
                        metadata.create_all(engine)

        # 4. Store result in context properties
        db_result = DatabaseBootstrapResult(
            config=db_config,
            engine=engine,
            session_factory=session_factory,
            uow=uow,
        )
        context.properties["database_result"] = db_result
        context.properties["db_engine"] = engine
        context.properties["db_session_factory"] = session_factory
        context.properties["db_uow"] = uow

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register database configuration schema under 'database'.

        Args:
            registry: Target ConfigRegistry instance.

        Returns:
            None.

        Raises:
            None.
        """
        register_database_config(registry)


__all__ = [
    "DatabaseBootstrapResult",
    "DatabaseBootstrapper",
]
