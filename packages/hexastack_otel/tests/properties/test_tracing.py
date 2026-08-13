from hexastack_otel.adapters.tracing import (
    InMemoryTracingAdapter,
    OtelTracingAdapter,
)
from hypothesis import given
from hypothesis import strategies as st

# W3C TraceContext requires non-zero 128-bit trace ID and 64-bit span ID
trace_id_strategy = st.integers(min_value=1, max_value=2**128 - 1).map(
    lambda n: f"{n:032x}"
)
span_id_strategy = st.integers(min_value=1, max_value=2**64 - 1).map(
    lambda n: f"{n:016x}"
)


@given(trace_id=trace_id_strategy, span_id=span_id_strategy)
def test_in_memory_context_extraction_roundtrip(trace_id: str, span_id: str):
    tracer = InMemoryTracingAdapter()
    carrier = {"traceparent": f"00-{trace_id}-{span_id}-01"}

    extracted = tracer.extract_context(carrier)
    assert extracted is not None
    assert extracted.trace_id == trace_id
    assert extracted.span_id == span_id


@given(trace_id=trace_id_strategy, span_id=span_id_strategy)
def test_otel_context_extraction_roundtrip(trace_id: str, span_id: str):
    tracer = OtelTracingAdapter(service_name="fuzz-service")
    carrier = {"traceparent": f"00-{trace_id}-{span_id}-01"}

    extracted = tracer.extract_context(carrier)
    assert extracted is not None
    assert extracted.trace_id == trace_id
    assert extracted.span_id == span_id
