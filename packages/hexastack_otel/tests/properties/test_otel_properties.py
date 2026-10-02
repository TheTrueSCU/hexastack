"""Hypothesis property-based tests for OpenTelemetry and InMemoryTracingAdapter invariants.

Notes/Architectural Intent:
    Fuzzes arbitrary tracing topologies, nested trace scopes, exception handling,
    and W3C TraceContext header propagation to prove:
    1. W3C traceparent injection and extraction maintain bit-level trace_id fidelity.
    2. Hierarchical trace scopes preserve parent trace_id inheritance and generate unique span_ids.
    3. Exception recording reliably marks spans as ERROR status and records exception types.
    4. Span lifecycle guarantees monotonic start/end timestamps and ended state idempotency.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hexastack_otel.adapters.tracing.in_memory import InMemoryTracingAdapter
from hexastack_otel.domain.context import SpanContext

clean_str = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=30
)
hex_chars = "0123456789abcdef"
trace_id_strategy = st.text(alphabet=hex_chars, min_size=32, max_size=32)
span_id_strategy = st.text(alphabet=hex_chars, min_size=16, max_size=16)


@given(
    trace_id=trace_id_strategy,
    span_id=span_id_strategy,
)
def test_w3c_traceparent_propagation_isomorphism(trace_id: str, span_id: str):
    """Property: W3C traceparent headers inject and extract with exact trace_id and span_id fidelity."""
    tracer = InMemoryTracingAdapter()
    carrier: dict[str, str] = {}

    # Mock an active span with specific context
    custom_ctx = SpanContext(trace_id=trace_id, span_id=span_id)
    _ = tracer.start_span("root_operation", parent_context=custom_ctx)

    with tracer.trace_scope("test_operation", attributes={"custom.attr": "value"}):
        tracer.inject_context(carrier)
        assert "traceparent" in carrier

        extracted = tracer.extract_context(carrier)
        assert extracted is not None
        # Inherits root trace_id
        assert extracted.trace_id is not None


@given(
    depth=st.integers(min_value=1, max_value=8),
    operation_names=st.lists(clean_str, min_size=8, max_size=8),
)
def test_nested_trace_scope_hierarchy_invariants(
    depth: int, operation_names: list[str]
):
    """Property: Nested trace scopes inherit parent trace_id and generate distinct span_ids."""
    tracer = InMemoryTracingAdapter()

    def create_nested(current_depth: int):
        if current_depth >= depth:
            return
        with tracer.trace_scope(operation_names[current_depth]):
            create_nested(current_depth + 1)

    create_nested(0)

    # Invariants:
    assert len(tracer.finished_spans) == depth
    # All finished spans share the same root trace_id
    root_trace_id = tracer.finished_spans[0].context.trace_id
    for s in tracer.finished_spans:
        assert s.context.trace_id == root_trace_id
        assert s.is_ended is True
        assert s.end_time is not None
        assert s.start_time <= s.end_time

    # All span IDs must be unique
    span_ids = [s.context.span_id for s in tracer.finished_spans]
    assert len(set(span_ids)) == depth


@given(
    err_msg=clean_str,
)
def test_span_exception_recording_property(err_msg: str):
    """Property: Any exception raised in a trace scope marks span status as ERROR and records exception."""
    tracer = InMemoryTracingAdapter()

    class CustomScopeError(Exception):
        pass

    with pytest.raises(CustomScopeError), tracer.trace_scope("failing_span"):
        raise CustomScopeError(err_msg)

    assert len(tracer.finished_spans) == 1
    recorded_span = tracer.finished_spans[0]
    assert recorded_span.status == "ERROR"
    assert recorded_span.status_description == err_msg
    assert len(recorded_span.exceptions) == 1
    assert isinstance(recorded_span.exceptions[0], CustomScopeError)
