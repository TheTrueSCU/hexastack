import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from hexastack_otel.domain.context import SpanContext
from hexastack_otel.ports.tracing import SpanPort, TracingPort

_current_in_memory_span: ContextVar["InMemorySpan | None"] = ContextVar(
    "current_in_memory_span", default=None
)


class InMemorySpan(SpanPort):
    """In-memory telemetry span recording all events, status, and attributes.

    Notes/Architectural Intent:
        Used for isolated unit and property testing without requiring OTel SDK
        runtime or live network collectors.
    """

    def __init__(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        context: SpanContext | None = None,
        parent_context: SpanContext | None = None,
    ) -> None:
        self.name = name
        self.attributes: dict[str, Any] = dict(attributes or {})
        self.context = context or SpanContext(
            trace_id=uuid.uuid4().hex,
            span_id=uuid.uuid4().hex[:16],
        )
        self.parent_context = parent_context
        self.status = "UNSET"
        self.status_description: str | None = None
        self.exceptions: list[BaseException] = []
        self.start_time: float = time.time()
        self.end_time: float | None = None
        self.is_ended: bool = False

    def end(self) -> None:
        """End the span recording."""
        if not self.is_ended:
            self.end_time = time.time()
            self.is_ended = True

    def record_exception(self, exception: BaseException) -> None:
        """Record an exception on the in-memory span."""
        self.exceptions.append(exception)
        self.set_status("ERROR", str(exception))

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a single key-value attribute on the span."""
        self.attributes[key] = value

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """Set multiple attributes on the span."""
        self.attributes.update(attributes)

    def set_status(self, status: str, description: str | None = None) -> None:
        """Set the span status ('OK', 'ERROR', 'UNSET')."""
        self.status = status
        self.status_description = description


class InMemoryTracingAdapter(TracingPort):
    """In-memory implementation of TracingPort for test isolation and assertions.

    Notes/Architectural Intent:
        Collects all finished spans in a local list, enabling assertions on span
        counts, tags, and exception capture in test suites.
    """

    def __init__(self) -> None:
        self.finished_spans: list[InMemorySpan] = []

    def clear(self) -> None:
        """Clear recorded finished spans."""
        self.finished_spans.clear()

    def extract_context(self, carrier: dict[str, str]) -> SpanContext | None:
        traceparent = carrier.get("traceparent") or carrier.get("TRACEPARENT")
        if not traceparent:
            return None
        parts = traceparent.split("-")
        if len(parts) >= 4:
            return SpanContext(trace_id=parts[1], span_id=parts[2])
        return None

    def get_current_span(self) -> InMemorySpan | None:
        return _current_in_memory_span.get()

    def get_spans_by_name(self, name: str) -> list[InMemorySpan]:
        """Find recorded spans matching name."""
        return [s for s in self.finished_spans if s.name == name]

    def inject_context(self, carrier: dict[str, str]) -> None:
        current = self.get_current_span()
        if current:
            ctx = current.context
            carrier["traceparent"] = f"00-{ctx.trace_id}-{ctx.span_id}-01"

    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        parent_context: SpanContext | None = None,
    ) -> InMemorySpan:
        parent = parent_context
        current = self.get_current_span()
        if parent is None and current is not None and isinstance(current, InMemorySpan):
            parent = current.context

        trace_id = parent.trace_id if parent else uuid.uuid4().hex
        span_ctx = SpanContext(
            trace_id=trace_id,
            span_id=uuid.uuid4().hex[:16],
        )

        return InMemorySpan(
            name=name,
            attributes=attributes,
            context=span_ctx,
            parent_context=parent,
        )

    @contextmanager
    def trace_scope(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[InMemorySpan]:
        span = self.start_span(name, attributes=attributes)
        token = _current_in_memory_span.set(span)
        try:
            yield span
        except BaseException as exc:
            span.record_exception(exc)
            raise
        finally:
            span.end()
            self.finished_spans.append(span)
            _current_in_memory_span.reset(token)


__all__ = [
    "InMemorySpan",
    "InMemoryTracingAdapter",
]
