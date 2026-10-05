from hexastack_core.domain.exceptions import HexastackError


class OtelError(HexastackError):
    """Base exception for all OpenTelemetry telemetry and tracing errors.

    Notes/Architectural Intent:
        Extends HexastackError to allow telemetry failures to be caught uniformly
        without leaking OpenTelemetry SDK internals into the core domain.
    """


class TracingConfigurationError(OtelError):
    """Exception raised when OpenTelemetry tracer initialization or endpoint config fails."""


__all__ = [
    "OtelError",
    "TracingConfigurationError",
]
