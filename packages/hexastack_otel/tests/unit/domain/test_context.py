from hexastack_otel.domain.context import SpanContext


def test_span_context_fields():
    ctx = SpanContext(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        trace_flags=1,
        trace_state="rojo=1",
    )
    assert ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx.span_id == "00f067aa0ba902b7"
    assert ctx.trace_flags == 1
    assert ctx.trace_state == "rojo=1"
