"""MCP Metrics Middleware for tracking Tool and Resource invocations."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.ports.metrics import MetricsPort


class McpMetricsMiddleware:
    """Middleware tracking MCP Tool, Prompt, and Resource execution counts and latencies.

    Notes/Architectural Intent:
        Wraps MCP tool execution with duration measurement, updating MetricsPort.
        Guarded via FeatureFlagPort.
    """

    def __init__(
        self,
        metrics: MetricsPort | None = None,
        flags: FeatureFlagPort | None = None,
    ) -> None:
        """Initialize McpMetricsMiddleware.

        Args:
            metrics: Optional MetricsPort instance to record into.
            flags: Optional FeatureFlagPort to dynamically evaluate metrics emission.
        """
        self._metrics = metrics
        self._flags = flags

    async def __call__(
        self,
        tool_name: str,
        handler: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute tool handler and record metrics."""
        if self._metrics is None:
            return await handler(*args, **kwargs)

        if self._flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not self._flags.is_enabled(
                "features.metrics.mcp", default=True, context=eval_ctx
            ):
                return await handler(*args, **kwargs)

        start_time = time.perf_counter()
        status = "success"
        try:
            return await handler(*args, **kwargs)
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.perf_counter() - start_time
            self._metrics.increment_counter(
                "mcp_tools_total",
                value=1.0,
                labels={"tool": tool_name, "status": status},
                description="Total MCP tools executed",
            )
            self._metrics.record_histogram(
                "mcp_tool_duration_seconds",
                value=duration,
                labels={"tool": tool_name},
                description="MCP tool duration distribution in seconds",
            )


__all__ = [
    "McpMetricsMiddleware",
]
