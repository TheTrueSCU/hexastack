import pytest

from hexastack_core.domain import Command, Event, Query
from hexastack_core.utils.context import (
    UserContext,
    correlation_scope,
    set_user_context,
)
from hexastack_otel.adapters.tracing import InMemoryTracingAdapter
from hexastack_otel.infra.middleware import TracingMiddleware


class CreateInvoiceCommand(Command):
    invoice_id: str
    amount: float


class GetInvoiceQuery(Query):
    invoice_id: str


class InvoiceCreatedEvent(Event):
    invoice_id: str


@pytest.mark.anyio
async def test_tracing_middleware_async_handler():
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer)

    async def _async_call(cmd):
        return f"async {cmd.invoice_id}"

    cmd = CreateInvoiceCommand(invoice_id="inv-4", amount=20.0)
    coro = middleware(cmd, _async_call)
    res = await coro
    assert res == "async inv-4"
    assert len(tracer.finished_spans) == 1
    assert tracer.finished_spans[0].name == "cqrs.CreateInvoiceCommand"


@pytest.mark.anyio
async def test_tracing_middleware_async_handler_exception():
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer)

    async def _async_failing_call(cmd):
        raise RuntimeError("Async boom")

    cmd = CreateInvoiceCommand(invoice_id="inv-5", amount=30.0)
    coro = middleware(cmd, _async_failing_call)
    with pytest.raises(RuntimeError, match="Async boom"):
        await coro

    assert len(tracer.finished_spans) == 1
    span = tracer.finished_spans[0]
    assert span.status == "ERROR"


def test_tracing_middleware_disabled():
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer, enabled=False)

    res = middleware(
        CreateInvoiceCommand(invoice_id="inv-3", amount=10.0), lambda cmd: "done"
    )
    assert res == "done"
    assert len(tracer.finished_spans) == 0


def test_tracing_middleware_dynamic_feature_flag():
    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )

    flags = InMemoryFeatureFlagAdapter({"features.otel.tracing": False})
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer, enabled=True, flags=flags)

    # 1. When flag is False, tracing is bypassed dynamically
    res = middleware(
        CreateInvoiceCommand(invoice_id="inv-dynamic", amount=15.0),
        lambda cmd: "bypassed",
    )
    assert res == "bypassed"
    assert len(tracer.finished_spans) == 0

    # 2. When flag is True, tracing activates dynamically
    flags.set_flag("features.otel.tracing", True)
    res_active = middleware(
        CreateInvoiceCommand(invoice_id="inv-dynamic", amount=15.0),
        lambda cmd: "active",
    )
    assert res_active == "active"
    assert len(tracer.finished_spans) == 1


def test_tracing_middleware_event_and_query_types():
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer)

    # Query message type
    middleware(GetInvoiceQuery(invoice_id="q1"), lambda q: "q_res")
    assert tracer.finished_spans[-1].attributes["message.type"] == "query"

    # Event message type
    middleware(InvoiceCreatedEvent(invoice_id="e1"), lambda e: "e_res")
    assert tracer.finished_spans[-1].attributes["message.type"] == "event"


def test_tracing_middleware_records_exceptions():
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer)

    def _failing_handler(cmd: CreateInvoiceCommand):
        raise ValueError("Invalid tax calculation")

    cmd = CreateInvoiceCommand(invoice_id="inv-2", amount=-1.0)
    with pytest.raises(ValueError, match="Invalid tax calculation"):
        middleware(cmd, _failing_handler)

    assert len(tracer.finished_spans) == 1
    span = tracer.finished_spans[0]
    assert span.status == "ERROR"
    assert (
        span.status_description is not None
        and "Invalid tax calculation" in span.status_description
    )


def test_tracing_middleware_with_command():
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer)

    with correlation_scope("corr-999"):
        set_user_context(UserContext(user_id="usr_abc", tenant_id="tenant_xyz"))
        cmd = CreateInvoiceCommand(invoice_id="inv-1", amount=99.0)
        res = middleware(cmd, lambda c: f"created {c.invoice_id}")
        assert res == "created inv-1"


def test_tracing_middleware_with_feature_flags():
    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )

    tracer = InMemoryTracingAdapter()
    flags = InMemoryFeatureFlagAdapter({"features.otel.tracing": False})
    middleware = TracingMiddleware(tracer=tracer, flags=flags)

    cmd = CreateInvoiceCommand(invoice_id="inv-disabled", amount=50.0)
    res = middleware(cmd, lambda c: "ok")
    assert res == "ok"
    assert len(tracer.finished_spans) == 0

    # Enable flag
    flags.set_flag("features.otel.tracing", True)
    res = middleware(cmd, lambda c: "ok")
    assert res == "ok"
    assert len(tracer.finished_spans) == 1


def test_tracing_middleware_with_tenant_and_user_context():
    """Verify tenant and user context attributes in TracingMiddleware."""
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer)

    set_user_context(UserContext(user_id="usr_123", tenant_id="tenant_456"))
    cmd = CreateInvoiceCommand(invoice_id="inv-ctx", amount=100.0)
    res = middleware(cmd, lambda c: "ok")
    assert res == "ok"
    assert len(tracer.finished_spans) == 1
    attrs = tracer.finished_spans[0].attributes
    assert attrs.get("user.id") == "usr_123"
    assert attrs.get("tenant.id") == "tenant_456"


@pytest.mark.anyio
async def test_tracing_middleware_async_handler_and_error():
    """Verify TracingMiddleware async execution and exception recording."""
    tracer = InMemoryTracingAdapter()
    middleware = TracingMiddleware(tracer=tracer)

    async def async_ok_handler(cmd):
        return "async_ok"

    cmd = CreateInvoiceCommand(invoice_id="inv-async", amount=20.0)
    res = await middleware(cmd, async_ok_handler)
    assert res == "async_ok"
    assert len(tracer.finished_spans) == 1

    async def async_err_handler(cmd):
        raise ValueError("async_error_test")

    with pytest.raises(ValueError, match="async_error_test"):
        await middleware(cmd, async_err_handler)

    assert len(tracer.finished_spans) == 2
    assert len(tracer.finished_spans[1].exceptions) == 1
