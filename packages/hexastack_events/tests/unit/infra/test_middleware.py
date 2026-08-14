import pytest

from hexastack_core.domain import Command, Event
from hexastack_core.utils.context import (
    UserContext,
    correlation_scope,
    set_user_context,
)
from hexastack_cqrs.adapters.buses import SynchronousCommandBus
from hexastack_cqrs.infra.pipeline import create_pipeline
from hexastack_cqrs.infra.registries import (
    CommandRegistry,
    HandlerRegistry,
)
from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage
from hexastack_events.domain.models import OutboxStatus
from hexastack_events.infra.middleware import OutboxCaptureMiddleware


class CreateOrderCommand(Command):
    order_id: str


class OrderCreatedDomainEvent(Event):
    order_id: str
    status: str = "CONFIRMED"


def test_outbox_capture_middleware_defaults():
    storage = InMemoryOutboxStorage()
    middleware = OutboxCaptureMiddleware(storage=storage)
    assert middleware._source == "hexastack"
    assert middleware._enabled is True


def test_outbox_capture_middleware():
    storage = InMemoryOutboxStorage()
    middleware = OutboxCaptureMiddleware(storage=storage, source="order-service")

    handler_reg = HandlerRegistry()
    command_reg = CommandRegistry()
    command_reg.register(CreateOrderCommand)

    # Handler emits OrderCreatedDomainEvent as return value
    def _create_order_handler(cmd: CreateOrderCommand):
        return OrderCreatedDomainEvent(order_id=cmd.order_id)

    handler_reg.register(CreateOrderCommand, _create_order_handler)

    command_bus = SynchronousCommandBus(handler_reg, middleware=[middleware])
    pipeline = create_pipeline(
        handler_registry=handler_reg,
        command_registry=command_reg,
        command_bus=command_bus,
    )

    with correlation_scope("corr-order-99"):
        set_user_context(UserContext(user_id="usr_buyer", tenant_id="tenant_omega"))
        res = pipeline.execute(CreateOrderCommand(order_id="ord-777"))
        assert isinstance(res, OrderCreatedDomainEvent)

    # Staged outbox record should exist
    records = storage.get_all()
    assert len(records) == 1
    rec = records[0]
    assert rec.event_type == "OrderCreatedDomainEvent"
    assert rec.source == "order-service"
    assert rec.payload["order_id"] == "ord-777"
    assert rec.correlation_id == "corr-order-99"
    assert rec.tenant_id == "tenant_omega"
    assert rec.status == OutboxStatus.PENDING


def test_outbox_capture_middleware_direct_event_instance():
    storage = InMemoryOutboxStorage()
    middleware = OutboxCaptureMiddleware(storage=storage, source="test-source")

    ev = OrderCreatedDomainEvent(order_id="direct-1")
    res = middleware(ev, lambda e: "handled")
    assert res == "handled"
    assert len(storage.get_all()) == 1
    assert storage.get_all()[0].payload["order_id"] == "direct-1"


def test_outbox_capture_middleware_disabled():
    storage = InMemoryOutboxStorage()
    middleware = OutboxCaptureMiddleware(storage=storage, enabled=False)

    ev = OrderCreatedDomainEvent(order_id="disabled-1")
    res = middleware(ev, lambda e: "handled")
    assert res == "handled"
    assert len(storage.get_all()) == 0


@pytest.mark.anyio
async def test_outbox_capture_middleware_async_handler():
    storage = InMemoryOutboxStorage()
    middleware = OutboxCaptureMiddleware(storage=storage, source="async-source")

    async def _async_handler(cmd):
        return OrderCreatedDomainEvent(order_id=cmd.order_id)

    cmd = CreateOrderCommand(order_id="async-99")
    res = await middleware(cmd, _async_handler)
    assert isinstance(res, OrderCreatedDomainEvent)
    assert len(storage.get_all()) == 1
    assert storage.get_all()[0].payload["order_id"] == "async-99"

    # Async handler returning non-event
    async def _async_string_handler(c):
        return "not-an-event"

    res2 = await middleware(cmd, _async_string_handler)
    assert res2 == "not-an-event"
    assert len(storage.get_all()) == 1
