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
