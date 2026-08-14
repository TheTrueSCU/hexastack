import types
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hexastack_core.domain import Command, Generic, Query
from hexastack_cqrs.adapters.buses.command.synchronous import (
    SynchronousCommandBus,
)
from hexastack_cqrs.adapters.buses.event.synchronous import (
    SynchronousEventBus,
)
from hexastack_cqrs.adapters.buses.query.synchronous import (
    SynchronousQueryBus,
)
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.command import CommandRegistry
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry
from hexastack_cqrs.infra.registries.query import QueryRegistry
from hexastack_fastapi.infra.autodiscovery import autodiscover_routes
from hexastack_fastapi.infra.decorators import api_command, api_query


@api_command("/auto/create", method="POST", status_code=201)
class AutoCreate(Command):
    item_id: str


@api_query("/auto/get", method="GET")
class AutoGet(Query):
    item_id: str


class AutoDTO(Generic):
    item_id: str


def test_route_autodiscovery_and_execution():
    handler_reg = HandlerRegistry()
    handler_reg.register(
        AutoCreate, lambda cmd: AutoDTO(item_id=f"created_{cmd.item_id}")
    )
    handler_reg.register(AutoGet, lambda qry: AutoDTO(item_id=f"got_{qry.item_id}"))

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=PresenterRegistry(),
    )

    app = FastAPI()
    app.state.pipeline = pipeline

    dummy_module = types.ModuleType("dummy_fastapi_endpoints")
    cast("Any", dummy_module).AutoCreate = AutoCreate
    cast("Any", dummy_module).AutoGet = AutoGet

    autodiscover_routes(app, packages_to_scan=[dummy_module])

    client = TestClient(app)

    # 1. Test autodiscovered command
    res_cmd = client.post("/auto/create", json={"item_id": "42"})
    assert res_cmd.status_code == 201
    assert res_cmd.json()["item_id"] == "created_42"

    # 2. Test autodiscovered query
    res_qry = client.get("/auto/get?item_id=42")
    assert res_qry.status_code == 200
    assert res_qry.json()["item_id"] == "got_42"
