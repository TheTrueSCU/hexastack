import pytest
from inline_snapshot import snapshot

from hexastack_otel.adapters.tracing.in_memory import InMemoryTracingAdapter


@pytest.mark.snapshot
def test_in_memory_span_lifecycle(in_memory_tracer: InMemoryTracingAdapter):
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


def test_in_memory_exception_capture(in_memory_tracer: InMemoryTracingAdapter):
    with (
        pytest.raises(ValueError, match="Database crashed"),
        in_memory_tracer.trace_scope("db.query"),
    ):
        raise ValueError("Database crashed")

    assert len(in_memory_tracer.finished_spans) == 1
    finished = in_memory_tracer.finished_spans[0]
    assert finished.status == "ERROR"
    assert "Database crashed" in finished.status_description
    assert len(finished.exceptions) == 1


def test_in_memory_context_injection(in_memory_tracer: InMemoryTracingAdapter):
    carrier: dict[str, str] = {}
    with in_memory_tracer.trace_scope("parent.call"):
        in_memory_tracer.inject_context(carrier)

    assert "traceparent" in carrier
    extracted = in_memory_tracer.extract_context(carrier)
    assert extracted is not None
