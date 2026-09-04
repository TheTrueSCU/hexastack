from dataclasses import dataclass
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import Session, sessionmaker

from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.ai import VectorStorePort
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_core.ports.unit_of_work import UnitOfWorkPort
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
    uow: SqlAlchemyUnitOfWork | AsyncSqlAlchemyUnitOfWork | UnitOfWorkPort
    vector_store: Any = None


class DatabaseBootstrapper(BootstrapperPort):
    """Bootstrap extension initializing SQLAlchemy engines, sessions, and UnitOfWork.

    Notes/Architectural Intent:
        Implements BootstrapperPort with order=15 (executing before CQRS order=20),
        registering database configuration under 'db' ([hexastack.db]) and injecting
        UnitOfWorkPort into DI. When auto_create_tables=True, runs create_all() on all
        metadata objects registered via register_metadata().
        When vector.enabled=True, initializes and binds PgVectorStoreAdapter.
    """

    name: str = "db"
    order: int = 15

    def _auto_create_tables(
        self,
        engine: Engine | AsyncEngine,
        async_mode: bool,
    ) -> None:
        """Create database tables across all registered metadata definitions."""
        registered = get_registered_metadata()
        if not registered:
            return

        if async_mode:
            sync_url = str(engine.url).replace("+aiosqlite", "").replace("+asyncpg", "")
            from sqlalchemy import create_engine as _ce
            from sqlalchemy.pool import NullPool

            _sync = _ce(sync_url, poolclass=NullPool)
            for metadata in registered:
                metadata.create_all(_sync)
            _sync.dispose()
        elif isinstance(engine, Engine):
            for metadata in registered:
                metadata.create_all(engine)

    def _configure_async_db(
        self,
        di: Any,
        db_config: HexastackDatabaseConfig,
    ) -> tuple[
        AsyncEngine, async_sessionmaker[AsyncSession], AsyncSqlAlchemyUnitOfWork, Any
    ]:
        """Initialize async database engine, session factory, UoW, and vector store."""
        async_engine = create_async_db_engine(db_config)
        async_factory = create_async_session_factory(async_engine)
        async_uow = AsyncSqlAlchemyUnitOfWork(session_factory=async_factory)

        if AsyncEngine not in di:
            di.add_instance(async_engine, declared_class=AsyncEngine)
        if AsyncSqlAlchemyUnitOfWork not in di:
            di.add_instance(async_uow, declared_class=AsyncSqlAlchemyUnitOfWork)

        vector_store = None
        if db_config.vector.enabled:
            from hexastack_db.adapters.vector import AsyncPgVectorStoreAdapter

            async_vector_store = AsyncPgVectorStoreAdapter(
                session_factory=async_factory,
                table_name=db_config.vector.table_name,
                dimension=db_config.vector.dimension,
            )
            if AsyncPgVectorStoreAdapter not in di:
                di.add_instance(
                    async_vector_store, declared_class=AsyncPgVectorStoreAdapter
                )
            vector_store = async_vector_store

        return async_engine, async_factory, async_uow, vector_store

    def _configure_sync_db(
        self,
        di: Any,
        db_config: HexastackDatabaseConfig,
    ) -> tuple[Engine, sessionmaker[Session], UnitOfWorkPort, Any]:
        """Initialize sync database engine, session factory, UoW, and vector store."""
        sync_engine = create_db_engine(db_config)
        sync_factory = create_session_factory(sync_engine)
        sync_uow = SqlAlchemyUnitOfWork(session_factory=sync_factory)

        if Engine not in di:
            di.add_instance(sync_engine, declared_class=Engine)
        if UnitOfWorkPort not in di:
            di.add_instance(sync_uow, declared_class=UnitOfWorkPort)
        if SqlAlchemyUnitOfWork not in di:
            di.add_instance(sync_uow, declared_class=SqlAlchemyUnitOfWork)

        uow = di.resolve(UnitOfWorkPort) if UnitOfWorkPort in di else sync_uow

        vector_store = None
        if db_config.vector.enabled:
            from hexastack_db.adapters.vector import PgVectorStoreAdapter

            sync_vector_store = PgVectorStoreAdapter(
                session_factory=sync_factory,
                table_name=db_config.vector.table_name,
                dimension=db_config.vector.dimension,
            )
            if db_config.auto_create_tables:
                sync_vector_store.create_table()
            di.add_instance(sync_vector_store, declared_class=VectorStorePort)
            di.add_instance(sync_vector_store, declared_class=PgVectorStoreAdapter)
            vector_store = sync_vector_store

        return sync_engine, sync_factory, uow, vector_store

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Assemble database engine, sessionmaker, and UnitOfWork in DI container.

        Args:
            context: BootstrapContext containing DI container and config.
        """
        di = context.container

        # 1. Read Database Configuration
        if HexastackDatabaseConfig in di:
            db_config = di.resolve(HexastackDatabaseConfig)
        else:
            db_config = context.get_config("db", HexastackDatabaseConfig)

        # 2. Build Engine & Session Factory based on async_mode
        if db_config.async_mode:
            engine, session_factory, uow, vector_store = self._configure_async_db(
                di, db_config
            )
        else:
            engine, session_factory, uow, vector_store = self._configure_sync_db(
                di, db_config
            )

        # 3. Run create_all on registered metadata if configured
        if db_config.auto_create_tables:
            self._auto_create_tables(engine, db_config.async_mode)

        # 4. Store result in context properties
        db_result = DatabaseBootstrapResult(
            config=db_config,
            engine=engine,
            session_factory=session_factory,
            uow=uow,
            vector_store=vector_store,
        )
        context.properties["db_result"] = db_result
        context.properties["database_result"] = db_result
        context.properties["engine"] = engine
        context.properties["db_engine"] = engine
        context.properties["session_factory"] = session_factory
        context.properties["db_session_factory"] = session_factory
        context.properties["uow"] = uow
        context.properties["db_uow"] = uow
        if vector_store is not None:
            context.properties["db_vector_store"] = vector_store

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register database configuration schema under 'db'.

        Args:
            registry: Target ConfigRegistry instance.
        """
        register_database_config(registry)


__all__ = [
    "DatabaseBootstrapper",
    "DatabaseBootstrapResult",
]
