import types
from typing import Any

from hexastack_core.domain import Command, Event, Generic, Query
from hexastack_core.infra import ConfigRegistry, ExceptionRegistry
from hexastack_core.ports import Presenter
from hexastack_cqrs.infra.autodiscovery import (
    autodiscover_cqrs,
)
from hexastack_cqrs.infra.decorators import (
    command_handler,
    config_section,
    event_listener,
    exception_handler,
    presenter,
    query_handler,
)
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from pydantic import BaseModel


class CreateOrder(Command):
    order_id: str


class GetOrder(Query[str]):
    order_id: str


class OrderFulfilled(Event):
    order_id: str


class OrderDTO(Generic):
    order_id: str


class DomainValidationError(Exception):
    pass


@config_section("cqrs.orders")
class OrderConfig(BaseModel):
    max_orders: int = 100


def test_autodiscover_cqrs_module():
    mod = types.ModuleType("dummy_handlers_mod")

    @command_handler(CreateOrder)
    def handle_create_order(cmd: CreateOrder) -> OrderDTO:
        return OrderDTO(order_id=cmd.order_id)

    @query_handler(GetOrder)
    def handle_get_order(qry: GetOrder) -> str:
        return f"found-{qry.order_id}"

    events_received: list[str] = []

    @event_listener(OrderFulfilled)
    def handle_order_fulfilled(evt: OrderFulfilled) -> None:
        events_received.append(evt.order_id)

    @presenter(OrderDTO, "json")
    class OrderJsonPresenter(Presenter):
        def present(self, instance: Generic) -> Any | None:
            if isinstance(instance, OrderDTO):
                return {"id": instance.order_id, "type": "order"}
            return None

    @exception_handler(DomainValidationError)
    def handle_validation_error(exc: DomainValidationError) -> dict[str, str]:
        return {"error": str(exc), "status": "bad_request"}

    def regular_helper() -> None:
        pass

    members = {
        "handle_create_order": handle_create_order,
        "handle_get_order": handle_get_order,
        "handle_order_fulfilled": handle_order_fulfilled,
        "OrderJsonPresenter": OrderJsonPresenter,
        "handle_validation_error": handle_validation_error,
        "OrderConfig": OrderConfig,
        "regular_helper": regular_helper,
    }
    for name, member in members.items():
        setattr(mod, name, member)

    exc_reg = ExceptionRegistry()
    config_reg = ConfigRegistry()
    pipeline = ExecutionPipeline(
        handler_registry=HandlerRegistry(),
        exception_registry=exc_reg,
    )

    autodiscover_cqrs(
        packages_or_modules=[mod],
        pipeline=pipeline,
        config_registry=config_reg,
    )

    # 1. Execute discovered command with discovered presenter
    res_cmd = pipeline.execute(CreateOrder(order_id="101"), output_format="json")
    assert res_cmd == {"id": "101", "type": "order"}

    # 2. Execute discovered query
    res_qry = pipeline.execute(GetOrder(order_id="202"))
    assert res_qry == "found-202"

    # 3. Publish discovered event
    pipeline.execute(OrderFulfilled(order_id="303"))
    assert events_received == ["303"]

    # 4. Discovered exception handler
    handled_err = exc_reg.handle(DomainValidationError("invalid order"))
    assert handled_err == {"error": "invalid order", "status": "bad_request"}

    # 5. Discovered config section
    assert "cqrs.orders" in config_reg
    assert config_reg.get("cqrs.orders") == OrderConfig
