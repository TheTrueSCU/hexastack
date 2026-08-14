import pytest

from hexastack_otel.adapters.tracing.otel import OtelTracingAdapter


def test_otel_span_lifecycle(otel_tracer: OtelTracingAdapter):
    with otel_tracer.trace_scope(
        "http.request", attributes={"http.method": "POST"}
    ) as span:
        span.set_attribute("http.status_code", 201)
        span.set_attributes({"client.ip": "127.0.0.1"})
        assert otel_tracer.get_current_span() is not None


def test_otel_exception_capture(otel_tracer: OtelTracingAdapter):
    with (
        pytest.raises(RuntimeError, match="Network timeout"),
        otel_tracer.trace_scope("grpc.call"),
    ):
        raise RuntimeError("Network timeout")


def test_otel_context_injection_and_extraction(otel_tracer: OtelTracingAdapter):
    carrier: dict[str, str] = {}
    with otel_tracer.trace_scope("parent.call"):
        otel_tracer.inject_context(carrier)

    assert "traceparent" in carrier
    extracted = otel_tracer.extract_context(carrier)
    assert extracted is not None
    assert len(extracted.trace_id) == 32
    assert len(extracted.span_id) == 16
