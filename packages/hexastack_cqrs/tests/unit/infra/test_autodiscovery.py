import types
from typing import Any

from pydantic import BaseModel
from rodi import Container

from hexastack_core.domain import Command, Event, Generic, Query
from hexastack_core.infra import ConfigRegistry, ExceptionRegistry
from hexastack_core.ports.presenter import PresenterPort
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
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry


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
    class OrderJsonPresenter(PresenterPort):
        def present(self, instance: Generic) -> Any | None:
            if isinstance(instance, OrderDTO):
                return {"id": instance.order_id, "type": "order"}
            return None

    # Class-based handler resolved via DI
    @command_handler(CreateOrder)
    class ClassCommandHandler:
        def __call__(self, cmd: CreateOrder) -> OrderDTO:
            return OrderDTO(order_id=f"class-{cmd.order_id}")

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

    # 6. Autodiscovery with DI container resolution
    container = Container()
    container.add_instance(ClassCommandHandler())
    container.add_instance(OrderJsonPresenter())
    mod_di = types.ModuleType("dummy_di_mod")
    setattr(mod_di, "ClassCommandHandler", ClassCommandHandler)  # noqa: B010
    setattr(mod_di, "OrderJsonPresenter", OrderJsonPresenter)  # noqa: B010

    pipeline_di = ExecutionPipeline(handler_registry=HandlerRegistry())
    autodiscover_cqrs(
        packages_or_modules=[mod_di],
        pipeline=pipeline_di,
        container=container,
    )
    res_di = pipeline_di.execute(CreateOrder(order_id="999"), output_format="json")
    assert res_di == {"id": "class-999", "type": "order"}


def test_cqrs_autodiscovery_isolated_helpers():
    from hexastack_core.infra.decorators import (
        ConfigMetadata,
        ExceptionMetadata,
    )
    from hexastack_cqrs.infra.autodiscovery import (
        _register_config,
        _register_exception,
        _register_handler,
        _register_presenter,
    )
    from hexastack_cqrs.infra.decorators import (
        HandlerMetadata,
        PresenterMetadata,
    )

    handler_reg = HandlerRegistry()
    pres_reg = PresenterRegistry()
    exc_reg = ExceptionRegistry()
    pipeline = ExecutionPipeline(
        handler_registry=handler_reg,
        presenter_registry=pres_reg,
        exception_registry=exc_reg,
    )

    # 1. _register_handler
    cmd_meta = HandlerMetadata(kind="command", target_cls=CreateOrder)
    _register_handler(lambda cmd: "handled", cmd_meta, pipeline, None)
    assert CreateOrder in handler_reg

    # 2. _register_presenter
    pres_meta = PresenterMetadata(target_cls=OrderDTO, output_format="text")
    _register_presenter(lambda x: str(x), pres_meta, pipeline, None)
    assert pres_reg.get(OrderDTO, "text") is not None

    # 3. _register_exception
    exc_meta = ExceptionMetadata(target_cls=DomainValidationError)
    _register_exception(lambda e: "caught", exc_meta, pipeline, None)
    assert DomainValidationError in exc_reg

    # 4. _register_config
    cfg_reg = ConfigRegistry()
    cfg_meta = ConfigMetadata(section_name="custom.test")
    _register_config(OrderConfig, cfg_meta, cfg_reg)
    assert "custom.test" in cfg_reg


def test_cqrs_autodiscovery_extra_branches():
    """Verify event subscription and class presenter instantiation in autodiscovery."""
    from hexastack_cqrs.adapters.buses.event.recording import RecordingEventBus
    from hexastack_cqrs.infra.autodiscovery import (
        _register_handler,
        _register_presenter,
    )
    from hexastack_cqrs.infra.decorators import HandlerMetadata, PresenterMetadata

    evt_bus = RecordingEventBus()
    pipeline = ExecutionPipeline(
        handler_registry=HandlerRegistry(),
        event_bus=evt_bus,
        presenter_registry=PresenterRegistry(),
    )

    # 1. Event handler registration
    evt_meta = HandlerMetadata(kind="event", target_cls=OrderFulfilled)
    _register_handler(lambda e: None, evt_meta, pipeline, None)

    # 2. Presenter as uninstantiated class without container
    class CustomClassPresenter(PresenterPort):
        def present(self, instance: Any) -> str:
            return f"presented:{instance}"

    p_meta = PresenterMetadata(target_cls=OrderDTO, output_format="custom_class")
    _register_presenter(CustomClassPresenter, p_meta, pipeline, None)
    assert pipeline._presenter_registry.get(OrderDTO, "custom_class") is not None
