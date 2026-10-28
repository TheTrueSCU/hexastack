import types

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
from hexastack_fastapi.infra.decorators import (
    api_command,
    api_query,
    webhook_receiver,
)


@api_command("/auto/create", method="POST", status_code=201)
class AutoCreate(Command):
    item_id: str


@api_query("/auto/get", method="GET")
class AutoGet(Query):
    item_id: str


class AutoDTO(Generic):
    item_id: str


class DummyWebhookVerifier:
    def verify(self, payload: bytes, headers: dict, secret: str) -> bool:
        if secret != "super_secret":  # pragma: allowlist secret
            return False
        return headers.get("x-signature") == "valid_sig"


@webhook_receiver(
    "/auto/webhook",
    verifier=DummyWebhookVerifier(),
    secret="super_secret",  # pragma: allowlist secret
    status_code=200,
)
class AutoWebhook(Command):
    item_id: str


def test_route_autodiscovery_and_execution():
    handler_reg = HandlerRegistry()
    handler_reg.register(
        AutoCreate, lambda cmd: AutoDTO(item_id=f"created_{cmd.item_id}")
    )
    handler_reg.register(AutoGet, lambda qry: AutoDTO(item_id=f"got_{qry.item_id}"))
    handler_reg.register(
        AutoWebhook, lambda cmd: AutoDTO(item_id=f"webhook_{cmd.item_id}")
    )

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
    dummy_module.__dict__["AutoCreate"] = AutoCreate
    dummy_module.__dict__["AutoGet"] = AutoGet
    dummy_module.__dict__["AutoWebhook"] = AutoWebhook

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

    # 3. Test autodiscovered webhook (valid signature)
    res_wh_valid = client.post(
        "/auto/webhook",
        json={"item_id": "wh_99"},
        headers={"x-signature": "valid_sig"},
    )
    assert res_wh_valid.status_code == 200
    assert res_wh_valid.json()["item_id"] == "webhook_wh_99"

    # 4. Test autodiscovered webhook (invalid signature)
    res_wh_invalid = client.post(
        "/auto/webhook",
        json={"item_id": "wh_99"},
        headers={"x-signature": "bad_sig"},
    )
    assert res_wh_invalid.status_code == 401
