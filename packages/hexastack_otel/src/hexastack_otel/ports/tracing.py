from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from hexastack_otel.domain.context import SpanContext


class SpanPort(ABC):
    """Abstract port representing an in-flight or completed telemetry span.

    Notes/Architectural Intent:
        Decouples span instrumentation from underlying tracing backends.
    """

    @abstractmethod
    def end(self) -> None:
        """Complete the span recording."""

    @abstractmethod
    def record_exception(self, exception: BaseException) -> None:
        """Record an exception on the span as a telemetry error event.

        Args:
            exception: The caught exception instance.
        """

    @abstractmethod
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a single key-value attribute on the span.

        Args:
            key: Attribute name string.
            value: Attribute value (primitive or list).
        """

    @abstractmethod
    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """Set multiple attributes on the span in a single call.

        Args:
            attributes: Dictionary of key-value attributes.
        """

    @abstractmethod
    def set_status(self, status: str, description: str | None = None) -> None:
        """Set the span status ('OK', 'ERROR', 'UNSET').

        Args:
            status: Status string identifier.
            description: Optional diagnostic message.
        """


class TracingPort(ABC):
    """Primary abstract port contract for distributed tracing and context propagation.

    Notes/Architectural Intent:
        Wraps OpenTelemetry tracer primitives into a clean hexagonal port interface.
        Allows switching between OTel SDK, console exporter, or mock in-memory
        recorders seamlessly.
    """

    @abstractmethod
    def extract_context(self, carrier: dict[str, str]) -> SpanContext | None:
        """Extract a SpanContext from an inbound dictionary carrier.

        Args:
            carrier: Inbound dictionary containing traceparent headers.

        Returns:
            Parsed SpanContext instance or None if no valid headers exist.
        """

    @abstractmethod
    def get_current_span(self) -> SpanPort | None:
        """Retrieve the currently active span in the current context/thread.

        Returns:
            Active SpanPort instance or None if no span is active.
        """

    @abstractmethod
    def inject_context(self, carrier: dict[str, str]) -> None:
        """Inject current trace context into an outbound dictionary carrier (e.g. HTTP headers).

        Args:
            carrier: Mutable dictionary to receive traceparent headers.
        """

    @abstractmethod
    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        parent_context: SpanContext | None = None,
    ) -> SpanPort:
        """Start a new telemetry span.

        Args:
            name: Span operation name.
            attributes: Optional key-value attributes to attach.
            parent_context: Optional parent SpanContext for remote linking.

        Returns:
            Active SpanPort instance.
        """

    @abstractmethod
    @contextmanager
    def trace_scope(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[SpanPort]:
        """Context manager creating a scoped span that automatically ends on exit.

        Args:
            name: Span operation name.
            attributes: Optional key-value attributes to attach.

        Yields:
            Active SpanPort instance within the context block.
        """


__all__ = [
    "SpanContext",
    "SpanPort",
    "TracingPort",
]
