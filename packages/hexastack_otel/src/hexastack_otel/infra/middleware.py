import inspect
from collections.abc import Callable
from typing import Any, cast

from hexastack_core.domain import Command, Generic, Query
from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.utils.context import get_correlation_id, get_user_context
from hexastack_otel.ports.tracing import TracingPort


class TracingMiddleware:
    """CQRS middleware wrapping Command and Query execution in OpenTelemetry spans.

    Notes/Architectural Intent:
        Automatically creates distributed telemetry spans with correlation ID,
        message type, tenant ID, and user ID attributes, recording execution
        failures without altering domain handler logic.
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

    def __call__[G: Generic, R](
        self,
        instance: G,
        next_call: Callable[[G], R],
    ) -> R:
        """Execute handler within a scoped telemetry span.

        Args:
            instance: Dispatched message instance.
            next_call: Downstream handler or next middleware in chain.

        Returns:
            The handler result of type R.
        """
        if not self._enabled:
            return next_call(instance)

        if self._flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not self._flags.is_enabled(
                "features.otel.tracing", default=True, context=eval_ctx
            ):
                return next_call(instance)

        span_name = f"cqrs.{instance.__class__.__name__}"
        attrs = self._build_attributes(instance)

        with self._tracer.trace_scope(span_name, attributes=attrs) as span:
            result = next_call(instance)

            if inspect.isawaitable(result):

                async def _async_wrap() -> Any:
                    try:
                        return await result
                    except BaseException as exc:
                        span.record_exception(exc)
                        raise

                return cast("R", _async_wrap())

            return result

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
