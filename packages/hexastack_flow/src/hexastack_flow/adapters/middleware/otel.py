"""OpenTelemetry step middleware adapter for Hexaflow workflows.

Notes/Architectural Intent:
    Implements StepMiddlewarePort to wrap individual workflow step executions in
    OpenTelemetry spans, recording execution status, attributes, and exceptions
    into Hexastack's TracingPort across both synchronous and asynchronous steps.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from hexaflow.domain.state import StepContext
from hexaflow.ports.middleware import StepMiddlewarePort

from hexastack_core.utils.imports import require_dependency

if TYPE_CHECKING:
    from hexastack_otel.ports.tracing import TracingPort

__all__ = [
    "OtelStepMiddleware",
]


class OtelStepMiddleware(StepMiddlewarePort):
    """Step middleware wrapping workflow step executions in OpenTelemetry spans.

    Notes/Architectural Intent:
        Implements StepMiddlewarePort to provide distributed tracing observability
        for individual step executions within Hexaflow workflows using Hexastack's TracingPort.
    """

    def __init__(self, tracer: TracingPort | None = None) -> None:
        """Initialize OtelStepMiddleware with a TracingPort instance.

        Args:
            tracer: Optional TracingPort instance. If not provided, resolves via hexastack-otel.

        Raises:
            MissingDependencyError: If hexastack-otel is not installed.
        """
        require_dependency(
            "hexastack_otel",
            extra="otel",
            package="hexastack-flow",
            feature_name="OpenTelemetry step middleware",
        )
        if tracer is None:
            from hexastack_otel.adapters.tracing.otel import OtelTracingAdapter

            tracer = OtelTracingAdapter()
        self._tracer = tracer

    def __call__[R](
        self,
        ctx: StepContext,
        next_call: Callable[[StepContext], R],
    ) -> R:
        """Wrap step execution in an OpenTelemetry trace scope.

        Args:
            ctx: Active StepContext providing step identity and metadata.
            next_call: Next callable in the step execution pipeline.

        Returns:
            The outcome payload of step execution or an awaitable coroutine.

        Raises:
            Exception: Any exception raised by the step action or downstream middlewares.
        """
        span_name = f"workflow.step.{ctx.step_name}"
        attributes: dict[str, Any] = {
            "workflow.attempt": ctx.attempt_number,
            "workflow.run_id": ctx.run_id,
            "workflow.step": ctx.step_name,
        }
        if ctx.stage_name:
            attributes["workflow.stage"] = ctx.stage_name

        scope = self._tracer.trace_scope(span_name, attributes=attributes)
        span = scope.__enter__()

        try:
            result = next_call(ctx)
        except BaseException as exc:
            span.set_status("ERROR", str(exc))
            scope.__exit__(type(exc), exc, exc.__traceback__)
            raise

        if inspect.isawaitable(result):

            async def _async_wrap() -> Any:
                try:
                    res = await result
                    span.set_status("OK")
                    scope.__exit__(None, None, None)
                    return res
                except BaseException as async_exc:
                    span.set_status("ERROR", str(async_exc))
                    scope.__exit__(type(async_exc), async_exc, async_exc.__traceback__)
                    raise

            return cast("R", _async_wrap())

        span.set_status("OK")
        scope.__exit__(None, None, None)
        return result
