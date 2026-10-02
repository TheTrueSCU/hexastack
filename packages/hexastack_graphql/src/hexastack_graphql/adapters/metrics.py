"""GraphQL Strawberry Metrics Extension."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from strawberry.extensions import SchemaExtension

from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.ports.metrics import MetricsPort


class StrawberryMetricsExtension(SchemaExtension):
    """Strawberry GraphQL schema extension recording operation duration and counts.

    Notes/Architectural Intent:
        Measures GraphQL execution performance and pushes counts/histograms into MetricsPort.
        Guarded via FeatureFlagPort.
    """

    def __init__(
        self,
        *,
        metrics: MetricsPort | None = None,
        flags: FeatureFlagPort | None = None,
        execution_context: Any = None,
    ) -> None:
        super().__init__(execution_context=execution_context)
        self.execution_context = execution_context
        self._metrics = metrics
        self._flags = flags

    def on_operation(self) -> Iterator[None]:
        start_time = time.perf_counter()
        yield
        if self._metrics is None:
            return

        if self._flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not self._flags.is_enabled(
                "features.metrics.graphql", default=True, context=eval_ctx
            ):
                return

        duration = time.perf_counter() - start_time
        op_name = self.execution_context.operation_name or (
            self.execution_context.query[:30]
            if self.execution_context.query
            else "anonymous"
        )
        self._metrics.increment_counter(
            "graphql_operations_total",
            value=1.0,
            labels={"operation": op_name},
            description="Total GraphQL operations processed",
        )
        self._metrics.record_histogram(
            "graphql_operation_duration_seconds",
            value=duration,
            labels={"operation": op_name},
            description="GraphQL operation duration distribution in seconds",
        )


__all__ = [
    "StrawberryMetricsExtension",
]
