from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.unit_of_work import UnitOfWorkPort
from hexastack_db.adapters.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from hexastack_db.infra.bootstrap import (
    DatabaseBootstrapper,
    DatabaseBootstrapResult,
)
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


def test_database_bootstrapper_order():
    bootstrapper = DatabaseBootstrapper()
    assert bootstrapper.name == "database"
    assert bootstrapper.order == 15
