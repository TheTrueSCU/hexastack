from typing import Any

from hexastack_core.domain import Command, Generic, Query
from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.utils.context import get_correlation_id, get_user_context
from hexastack_cqrs.infra.middleware.generic import InOutMiddleware
from hexastack_otel.ports.tracing import TracingPort


class TracingMiddleware(InOutMiddleware):
    """CQRS middleware wrapping Command and Query execution in OpenTelemetry spans.

    Notes/Architectural Intent:
        Inherits from InOutMiddleware to automatically create distributed telemetry
        spans with correlation ID, message type, tenant ID, and user ID attributes,
        recording execution failures via on_error() without altering domain handler logic.
        Respects dynamic feature flag evaluation via FeatureFlagPort.
    """

    def __init__(
        self,
        tracer: TracingPort,
        enabled: bool = True,
        flags: FeatureFlagPort | None = None,
    ) -> None:
        """Initialize tracing middleware with a TracingPort implementation.

        Args:
            tracer: TracingPort instance (Otel or InMemory).
            enabled: Whether span creation is active.
            flags: Optional FeatureFlagPort to dynamically evaluate tracing activation.
        """
        self._tracer = tracer
        self._enabled = enabled
        self._flags = flags

    def before(self, instance: Generic) -> Any:
        """Open a scoped telemetry span before downstream handler execution.

        Args:
            instance: Dispatched message instance.

        Returns:
            Dictionary context with active span and context manager or inactive flag.
        """
        if not self._enabled:
            return {"active": False}

        if self._flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not self._flags.is_enabled(
                "features.otel.tracing", default=True, context=eval_ctx
            ):
                return {"active": False}

        span_name = f"cqrs.{instance.__class__.__name__}"
        attrs = self._build_attributes(instance)

        scope = self._tracer.trace_scope(span_name, attributes=attrs)
        span = scope.__enter__()
        return {"active": True, "scope": scope, "span": span}

    def after(self, instance: Generic, result: Any, context: Any) -> Any:
        """Close the scoped telemetry span on successful execution.

        Args:
            instance: Dispatched message instance.
            result: Handler return value.
            context: Context dictionary returned by before().

        Returns:
            Unmodified handler result.
        """
        if isinstance(context, dict) and context.get("active"):
            scope = context.get("scope")
            if scope is not None:
                scope.__exit__(None, None, None)
        return result

    def on_error(self, instance: Generic, exc: Exception, context: Any) -> None:
        """Close the telemetry scope when an exception occurs during execution.

        Args:
            instance: Dispatched message instance.
            exc: Exception raised during execution.
            context: Context dictionary returned by before().
        """
        if isinstance(context, dict) and context.get("active"):
            scope = context.get("scope")
            if scope is not None:
                scope.__exit__(type(exc), exc, exc.__traceback__)

    def _build_attributes(self, instance: Generic) -> dict[str, Any]:
        """Construct standard telemetry attributes from message context."""
        msg_name = instance.__class__.__name__
        msg_type = (
            "command"
            if isinstance(instance, Command)
            else ("query" if isinstance(instance, Query) else "event")
        )

        attributes: dict[str, Any] = {
            "message.name": msg_name,
            "message.type": msg_type,
        }

        cid = get_correlation_id()
        if cid:
            attributes["correlation.id"] = cid

        user_ctx = get_user_context()
        if user_ctx:
            if user_ctx.tenant_id:
                attributes["tenant.id"] = user_ctx.tenant_id
            if user_ctx.user_id:
                attributes["user.id"] = user_ctx.user_id

        return attributes


__all__ = [
    "TracingMiddleware",
]
