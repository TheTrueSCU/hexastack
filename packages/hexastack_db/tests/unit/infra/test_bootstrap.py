from rodi import Container
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.ai import VectorStorePort
from hexastack_core.ports.unit_of_work import UnitOfWorkPort
from hexastack_db.adapters.unit_of_work import (
    AsyncSqlAlchemyUnitOfWork,
    SqlAlchemyUnitOfWork,
)
from hexastack_db.adapters.vector import (
    AsyncPgVectorStoreAdapter,
    PgVectorStoreAdapter,
)
from hexastack_db.infra.bootstrap import (
    DatabaseBootstrapper,
    DatabaseBootstrapResult,
)
from hexastack_db.infra.config import HexastackDatabaseConfig, PgVectorConfig


def test_database_bootstrapper_order():
    bootstrapper = DatabaseBootstrapper()
    assert bootstrapper.name == "db"
    assert bootstrapper.order == 15


def test_database_bootstrapper_sync():
    result = bootstrap(bootstrappers=[DatabaseBootstrapper()])
    container = result.container

    assert Engine in container
    assert UnitOfWorkPort in container
    assert SqlAlchemyUnitOfWork in container

    db_res: DatabaseBootstrapResult = result.get("database_result")
    assert db_res is not None
    assert isinstance(db_res.engine, Engine)
    assert isinstance(db_res.uow, SqlAlchemyUnitOfWork)
    assert db_res.vector_store is None

    assert result.get("db_session_factory") is not None
    assert result.get("db_uow") is db_res.uow


def test_database_bootstrapper_with_vector_sync():
    config = HexastackDatabaseConfig(
        url="sqlite:///:memory:",
        vector=PgVectorConfig(enabled=True, table_name="custom_vec"),
        auto_create_tables=True,
    )

    c = Container()
    c.add_instance(config, declared_class=HexastackDatabaseConfig)

    result = bootstrap(
        bootstrappers=[DatabaseBootstrapper()],
        container=c,
    )
    container = result.container

    assert VectorStorePort in container
    assert PgVectorStoreAdapter in container
    vec_store = container.resolve(VectorStorePort)
    assert isinstance(vec_store, PgVectorStoreAdapter)

    db_res: DatabaseBootstrapResult = result.get("database_result")
    assert db_res.vector_store is vec_store
    assert result.get("db_vector_store") is vec_store


def test_database_bootstrapper_async_with_vector():
    config = HexastackDatabaseConfig(
        url="sqlite+aiosqlite:///:memory:",
        async_mode=True,
        vector=PgVectorConfig(enabled=True, table_name="async_vec"),
        auto_create_tables=True,
    )

    c = Container()
    c.add_instance(config, declared_class=HexastackDatabaseConfig)

    result = bootstrap(
        bootstrappers=[DatabaseBootstrapper()],
        container=c,
    )
    container = result.container

    assert AsyncEngine in container
    assert AsyncSqlAlchemyUnitOfWork in container
    assert AsyncPgVectorStoreAdapter in container

    vec_store = container.resolve(AsyncPgVectorStoreAdapter)
    assert isinstance(vec_store, AsyncPgVectorStoreAdapter)

    db_res: DatabaseBootstrapResult = result.get("database_result")
    assert db_res is not None
    assert db_res.vector_store is vec_store
    assert result.get("db_vector_store") is vec_store
    assert result.get("db_engine") is not None
    assert result.get("db_session_factory") is not None
    assert result.get("db_uow") is not None
