from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.ai import VectorStorePort
from hexastack_core.ports.unit_of_work import UnitOfWorkPort
from hexastack_db.adapters.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from hexastack_db.adapters.vector import PgVectorStoreAdapter
from hexastack_db.infra.bootstrap import (
    DatabaseBootstrapper,
    DatabaseBootstrapResult,
)
from hexastack_db.infra.config import HexastackDatabaseConfig, PgVectorConfig
from rodi import Container
from sqlalchemy import Engine


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


def test_database_bootstrapper_with_vector():
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


def test_database_bootstrapper_order():
    bootstrapper = DatabaseBootstrapper()
    assert bootstrapper.name == "db"
    assert bootstrapper.order == 15
