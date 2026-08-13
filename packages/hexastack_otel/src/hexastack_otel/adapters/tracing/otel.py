from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.trace import (
    NonRecordingSpan,
    StatusCode,
    TraceFlags,
    TraceState,
)
from opentelemetry.trace import (
    Span as OtelRawSpan,
)
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)

from hexastack_otel.domain.context import SpanContext
from hexastack_otel.ports.tracing import SpanPort, TracingPort


class OtelSpan(SpanPort):
    """Concrete wrapper around an OpenTelemetry SDK Span."""

    def __init__(self, raw_span: OtelRawSpan) -> None:
        self._span = raw_span

    def set_attribute(self, key: str, value: Any) -> None:
        self._span.set_attribute(key, value)

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        self._span.set_attributes(attributes)

    def record_exception(self, exception: BaseException) -> None:
        self._span.record_exception(exception)
        self._span.set_status(StatusCode.ERROR, str(exception))

    def set_status(self, status: str, description: str | None = None) -> None:
        code = StatusCode.OK if status.upper() == "OK" else StatusCode.ERROR
        self._span.set_status(code, description)

    def end(self) -> None:
        self._span.end()


class OtelTracingAdapter(TracingPort):
    """Production OpenTelemetry SDK adapter supporting OTLP, Console, and custom exporters.

    Notes/Architectural Intent:
        Implements TracingPort using opentelemetry-sdk. Supports W3C TraceContext
        header injection and extraction across distributed service boundaries.
    """

    def __init__(
        self,
        service_name: str = "hexastack-app",
        tracer_provider: TracerProvider | None = None,
        exporter: SpanExporter | None = None,
    ) -> None:
        self._service_name = service_name
        self._propagator = TraceContextTextMapPropagator()

        if tracer_provider is not None:
            self._provider = tracer_provider
        else:
            resource = Resource.create({"service.name": service_name})
            self._provider = TracerProvider(resource=resource)
            if exporter is not None:
                self._provider.add_span_processor(SimpleSpanProcessor(exporter))

        self._tracer = self._provider.get_tracer("hexastack", "0.1.0")

    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        parent_context: SpanContext | None = None,
    ) -> OtelSpan:
        context = None
        if parent_context:
            otel_span_context = trace.SpanContext(
                trace_id=int(parent_context.trace_id, 16),
                span_id=int(parent_context.span_id, 16),
                is_remote=True,
                trace_flags=TraceFlags(parent_context.trace_flags),
                trace_state=TraceState.from_header([parent_context.trace_state])
                if parent_context.trace_state
                else None,
            )
            context = trace.set_span_in_context(NonRecordingSpan(otel_span_context))

        raw = self._tracer.start_span(name, attributes=attributes, context=context)
        return OtelSpan(raw)

    @contextmanager
    def trace_scope(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[OtelSpan]:
        with self._tracer.start_as_current_span(name, attributes=attributes) as raw:
            yield OtelSpan(raw)

    def get_current_span(self) -> OtelSpan | None:
        raw = trace.get_current_span()
        if raw and raw.is_recording():
            return OtelSpan(raw)
        return None

    def inject_context(self, carrier: dict[str, str]) -> None:
        self._propagator.inject(carrier)

    def extract_context(self, carrier: dict[str, str]) -> SpanContext | None:
        ctx = self._propagator.extract(carrier)
        current = trace.get_current_span(ctx)
        span_ctx = current.get_span_context()
        if span_ctx.is_valid:
            return SpanContext(
                trace_id=f"{span_ctx.trace_id:032x}",
                span_id=f"{span_ctx.span_id:016x}",
                trace_flags=int(span_ctx.trace_flags),
            )
        return None


__all__ = [
    "OtelSpan",
    "OtelTracingAdapter",
]
