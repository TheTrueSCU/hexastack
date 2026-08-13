from dataclasses import dataclass


@dataclass(frozen=True)
class SpanContext:
    """Immutable representation of a distributed trace context.

    Notes/Architectural Intent:
        Standardized representation of W3C TraceContext headers (traceparent)
        for cross-service context propagation. Represents pure domain context.
    """

    trace_id: str
    span_id: str
    trace_flags: int = 1
    trace_state: str = ""


__all__ = [
    "SpanContext",
]
