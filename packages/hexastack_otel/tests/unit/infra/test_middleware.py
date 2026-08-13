import pytest
from hexastack_core.domain import Command, Query
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
from hexastack_otel.adapters.tracing import InMemoryTracingAdapter
from hexastack_otel.infra.middleware import TracingMiddleware


class CreateInvoiceCommand(Command):
    invoice_id: str
    amount: float


class GetInvoiceQuery(Query):
    invoice_id: str


def test_tracing_middleware_with_command():
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer)

    handler_reg = HandlerRegistry()
    command_reg = CommandRegistry()
    command_reg.register(CreateInvoiceCommand)

    handler_reg.register(CreateInvoiceCommand, lambda cmd: f"created {cmd.invoice_id}")

    command_bus = SynchronousCommandBus(handler_reg, middleware=[middleware])
    pipeline = create_pipeline(
        handler_registry=handler_reg,
        command_registry=command_reg,
        command_bus=command_bus,
    )

    with correlation_scope("corr-999"):
        set_user_context(UserContext(user_id="usr_abc", tenant_id="tenant_xyz"))
        res = pipeline.execute(CreateInvoiceCommand(invoice_id="inv-1", amount=99.0))
        assert res == "created inv-1"

    assert len(tracer.finished_spans) == 1
    span = tracer.finished_spans[0]
    assert span.name == "cqrs.CreateInvoiceCommand"
    assert span.attributes["message.name"] == "CreateInvoiceCommand"
    assert span.attributes["message.type"] == "command"
    assert span.attributes["correlation.id"] == "corr-999"
    assert span.attributes["tenant.id"] == "tenant_xyz"
    assert span.attributes["user.id"] == "usr_abc"
    assert span.status != "ERROR"


def test_tracing_middleware_records_exceptions():
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer)

    handler_reg = HandlerRegistry()
    command_reg = CommandRegistry()
    command_reg.register(CreateInvoiceCommand)

    def _failing_handler(cmd: CreateInvoiceCommand):
        raise ValueError("Invalid tax calculation")

    handler_reg.register(CreateInvoiceCommand, _failing_handler)

    command_bus = SynchronousCommandBus(handler_reg, middleware=[middleware])
    pipeline = create_pipeline(
        handler_registry=handler_reg,
        command_registry=command_reg,
        command_bus=command_bus,
    )

    with pytest.raises(ValueError, match="Invalid tax calculation"):
        pipeline.execute(CreateInvoiceCommand(invoice_id="inv-2", amount=-1.0))

    assert len(tracer.finished_spans) == 1
    span = tracer.finished_spans[0]
    assert span.status == "ERROR"
    assert (
        span.status_description is not None
        and "Invalid tax calculation" in span.status_description
    )
