"""CQRS Pipeline Metrics Middleware."""

from __future__ import annotations

import time
from typing import Any

from hexastack_core.domain import Command, Generic
from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.ports.metrics import MetricsPort
from hexastack_cqrs.infra.middleware.generic import InOutMiddleware


class CqrsMetricsMiddleware(InOutMiddleware):
    """CQRS middleware recording Command/Query throughput and execution durations.

    Notes/Architectural Intent:
        Intercepts CQRS messages in the execution pipeline, measuring execution latency
        and recording status tags against MetricsPort. Guarded via FeatureFlagPort.
    """

    def __init__(
        self,
        metrics: MetricsPort,
        enabled: bool = True,
        flags: FeatureFlagPort | None = None,
    ) -> None:
        """Initialize CQRS metrics middleware.

        Args:
            metrics: MetricsPort instance.
            enabled: Master activation toggle.
            flags: Optional FeatureFlagPort to dynamically evaluate metrics emission.
        """
        self._metrics = metrics
        self._enabled = enabled
        self._flags = flags

    def before(self, instance: Generic) -> Any:
        """Capture start time before handler invocation."""
        if not self._enabled:
            return {"active": False}

        if self._flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not self._flags.is_enabled(
                "features.metrics.cqrs", default=True, context=eval_ctx
            ):
                return {"active": False}

        return {
            "active": True,
            "start_time": time.perf_counter(),
            "name": instance.__class__.__name__,
            "type": "command" if isinstance(instance, Command) else "query",
        }

    def after(self, instance: Generic, result: Any, context: Any) -> Any:
        """Record success metric after handler execution."""
        if not context.get("active", False):
            return result

        duration = time.perf_counter() - context["start_time"]
        name = context["name"]
        msg_type = context["type"]

        self._metrics.increment_counter(
            "cqrs_messages_total",
            value=1.0,
            labels={"name": name, "type": msg_type, "status": "success"},
            description="Total CQRS messages executed",
        )
        self._metrics.record_histogram(
            "cqrs_message_duration_seconds",
            value=duration,
            labels={"name": name, "type": msg_type},
            description="CQRS message execution duration distribution in seconds",
        )
        return result

    def on_error(self, instance: Generic, exc: Exception, context: Any) -> None:
        """Record failure metric upon exception."""
        if not context.get("active", False):
            return

        duration = time.perf_counter() - context["start_time"]
        name = context["name"]
        msg_type = context["type"]

        self._metrics.increment_counter(
            "cqrs_messages_total",
            value=1.0,
            labels={"name": name, "type": msg_type, "status": "error"},
            description="Total CQRS messages executed",
        )
        self._metrics.record_histogram(
            "cqrs_message_duration_seconds",
            value=duration,
            labels={"name": name, "type": msg_type},
            description="CQRS message execution duration distribution in seconds",
        )


__all__ = [
    "CqrsMetricsMiddleware",
]
