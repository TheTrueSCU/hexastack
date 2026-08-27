import pytest

from hexastack_otel.adapters.tracing.otel import OtelSpan, OtelTracingAdapter
from hexastack_otel.domain.context import SpanContext


def test_otel_context_injection_and_extraction(otel_tracer: OtelTracingAdapter):
    carrier: dict[str, str] = {}
    with otel_tracer.trace_scope("parent.call"):
        otel_tracer.inject_context(carrier)

    assert "traceparent" in carrier
    extracted = otel_tracer.extract_context(carrier)
    assert extracted is not None
    assert len(extracted.trace_id) == 32
    assert len(extracted.span_id) == 16
    assert isinstance(extracted.trace_flags, int)
    assert extracted.trace_flags > 0

    # Extracting from invalid/empty carrier returns None
    assert otel_tracer.extract_context({}) is None


def test_otel_exception_capture(otel_tracer: OtelTracingAdapter):
    with (
        pytest.raises(RuntimeError, match="Network timeout"),
        otel_tracer.trace_scope("grpc.call") as span,
    ):
        span.record_exception(RuntimeError("Network timeout"))
        raise RuntimeError("Network timeout")


def test_otel_span_lifecycle(otel_tracer: OtelTracingAdapter):
    with otel_tracer.trace_scope(
        "http.request", attributes={"http.method": "POST"}
    ) as span:
        span.set_attribute("http.status_code", 201)
        span.set_attributes({"client.ip": "127.0.0.1"})
        span.set_status("OK", "Successful request")
        assert otel_tracer.get_current_span() is not None

    # Error status branch
    span_explicit = otel_tracer.start_span("explicit.span")
    span_explicit.set_status("ERROR", "Explicit error")
    span_explicit.end()


def test_otel_start_span_with_parent_context(otel_tracer: OtelTracingAdapter):
    parent = SpanContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=1,
        trace_state="congo=t61rcWkgMzE",
    )
    span = otel_tracer.start_span("child.span", parent_context=parent)
    assert isinstance(span, OtelSpan)
    span.end()


def test_otel_custom_tracer_provider_and_inactive_span():
    from opentelemetry.sdk.trace import TracerProvider

    custom_provider = TracerProvider()
    adapter = OtelTracingAdapter(
        service_name="custom-svc", tracer_provider=custom_provider
    )
    assert adapter._provider is custom_provider
    # Outside any active span context, get_current_span returns None
    assert adapter.get_current_span() is None
