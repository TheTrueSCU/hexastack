import pytest
from inline_snapshot import snapshot

from hexastack_otel.adapters.tracing.in_memory import (
    InMemorySpan,
    InMemoryTracingAdapter,
)


def test_explicit_parent_context_overrides_current(
    in_memory_tracer: InMemoryTracingAdapter,
):
    """Kills mutant 903 (parent = parent_context): explicit parent takes priority."""
    from hexastack_otel.domain.context import SpanContext

    explicit_parent = SpanContext(trace_id="explicit-trace-id-abc", span_id="span-001")
    span = in_memory_tracer.start_span("explicit.child", parent_context=explicit_parent)
    assert span.parent_context is explicit_parent
    assert span.context.trace_id == "explicit-trace-id-abc"


def test_extract_context_from_traceparent(in_memory_tracer: InMemoryTracingAdapter):
    """Kills mutant 921: extract_context reads 'traceparent' key (not TRACEPARENT)."""
    carrier = {"traceparent": "00-abc123trace-span456-01"}
    ctx = in_memory_tracer.extract_context(carrier)
    assert ctx is not None
    assert ctx.trace_id == "abc123trace"
    assert ctx.span_id == "span456"


def test_extract_context_returns_none_for_missing_key(
    in_memory_tracer: InMemoryTracingAdapter,
):
    assert in_memory_tracer.extract_context({}) is None


def test_extract_context_uppercase_fallback(in_memory_tracer: InMemoryTracingAdapter):
    """Kills mutant 921: extract_context also reads 'TRACEPARENT' uppercase key."""
    carrier = {"TRACEPARENT": "00-uppertraceabc-upperspanxyz-01"}
    ctx = in_memory_tracer.extract_context(carrier)
    assert ctx is not None
    assert ctx.trace_id == "uppertraceabc"
    assert ctx.span_id == "upperspanxyz"


# ---------------------------------------------------------------------------
# Exception capture (kills status, status_description, exceptions mutants)
# ---------------------------------------------------------------------------


def test_in_memory_exception_capture(in_memory_tracer: InMemoryTracingAdapter):
    """Kills mutants 884–887 via ERROR status path."""
    with (
        pytest.raises(ValueError, match="Database crashed"),
        in_memory_tracer.trace_scope("db.query"),
    ):
        raise ValueError("Database crashed")

    assert len(in_memory_tracer.finished_spans) == 1
    finished = in_memory_tracer.finished_spans[0]
    assert finished.status == "ERROR"
    assert finished.status_description == "Database crashed"
    assert len(finished.exceptions) == 1
    assert isinstance(finished.exceptions[0], ValueError)


def test_in_memory_span_end_is_idempotent():
    """Kills mutant 899: end_time only set once (is_ended guard)."""
    span = InMemorySpan("idempotent")
    span.end()
    t1 = span.end_time
    span.end()
    t2 = span.end_time
    assert span.is_ended is True
    assert t1 == t2  # second call is a no-op


def test_in_memory_span_initial_state():
    """Kills mutants 884–893: initial status, is_ended, end_time, start_time."""
    span = InMemorySpan("init.test")
    assert span.status == "UNSET"
    assert span.status_description is None
    assert span.is_ended is False
    assert span.end_time is None
    assert span.start_time > 0
    assert span.exceptions == []
    assert span.attributes == {}
    assert span.parent_context is None


# ---------------------------------------------------------------------------
# Span lifecycle — field assignments (kills is_ended, end_time, status mutants)
# ---------------------------------------------------------------------------


@pytest.mark.snapshot
def test_in_memory_span_lifecycle(in_memory_tracer: InMemoryTracingAdapter):
    """Kills mutants 892–893 (is_ended), 899 (end_time), 884–887 (status/UNSET)."""
    with in_memory_tracer.trace_scope(
        "test.operation", attributes={"env": "test"}
    ) as span:
        span.set_attribute("user.id", "u_42")
        span.set_attributes({"tier": "gold", "retry": 1})
        assert in_memory_tracer.get_current_span() is span

    assert len(in_memory_tracer.finished_spans) == 1
    finished = in_memory_tracer.finished_spans[0]

    assert {
        "name": finished.name,
        "attributes": finished.attributes,
        "is_ended": finished.is_ended,
        "status": finished.status,
    } == snapshot(
        {
            "name": "test.operation",
            "attributes": {
                "env": "test",
                "user.id": "u_42",
                "tier": "gold",
                "retry": 1,
            },
            "is_ended": True,
            "status": "UNSET",
        }
    )

    # Explicit field assertions kill individual assignment mutants
    assert finished.is_ended is True
    assert finished.end_time is not None
    assert finished.end_time > 0
    assert finished.status == "UNSET"  # no exception — stays UNSET


def test_inject_context_no_active_span(in_memory_tracer: InMemoryTracingAdapter):
    """Carrier stays empty when no active span exists."""
    carrier: dict[str, str] = {}
    in_memory_tracer.inject_context(carrier)
    assert carrier == {}


# ---------------------------------------------------------------------------
# Context injection — traceparent format (kills mutants 918, 921)
# ---------------------------------------------------------------------------


def test_inject_context_traceparent_format(in_memory_tracer: InMemoryTracingAdapter):
    """Kills mutant 918: traceparent must be '00-<trace_id>-<span_id>-01'."""
    carrier: dict[str, str] = {}
    with in_memory_tracer.trace_scope("parent.call") as span:
        in_memory_tracer.inject_context(carrier)

    assert "traceparent" in carrier
    parts = carrier["traceparent"].split("-")
    assert len(parts) == 4
    assert parts[0] == "00"
    assert parts[1] == span.context.trace_id
    assert parts[2] == span.context.span_id
    assert parts[3] == "01"


# ---------------------------------------------------------------------------
# Nested spans — parent context inheritance (kills mutants 903–910)
# ---------------------------------------------------------------------------


def test_nested_span_inherits_parent_trace_id(in_memory_tracer: InMemoryTracingAdapter):
    """Kills mutants 903–910: parent context propagation in start_span."""
    with (
        in_memory_tracer.trace_scope("parent.op") as parent_span,
        in_memory_tracer.trace_scope("child.op") as child_span,
    ):
        assert child_span.parent_context is not None
        # Child shares parent's trace_id
        assert child_span.context.trace_id == parent_span.context.trace_id
        # Child has its own span_id
        assert child_span.context.span_id != parent_span.context.span_id


def test_top_level_span_has_no_parent(in_memory_tracer: InMemoryTracingAdapter):
    """Kills mutant 905: parent is None when no current span exists."""
    with in_memory_tracer.trace_scope("root.op") as span:
        assert span.parent_context is None


def test_in_memory_span_unset_status_and_query_by_name(
    in_memory_tracer: InMemoryTracingAdapter,
):
    span = in_memory_tracer.start_span("custom.metric.op", attributes={"key": "val"})
    assert span.status == "UNSET"
    assert span.status_description is None
    assert span.is_ended is False
    assert span.attributes["key"] == "val"
    assert len(span.context.span_id) == 16
    assert len(span.context.trace_id) == 32

    # End span
    span.end()
    assert span.is_ended is True
    end_time_first = span.end_time
    assert end_time_first is not None

    # Idempotent double end()
    span.end()
    assert span.end_time == end_time_first

    # Query finished spans by name
    in_memory_tracer.finished_spans.append(span)
    matches = in_memory_tracer.get_spans_by_name("custom.metric.op")
    assert len(matches) == 1
    assert matches[0] is span

    no_matches = in_memory_tracer.get_spans_by_name("non_existent_op")
    assert len(no_matches) == 0
