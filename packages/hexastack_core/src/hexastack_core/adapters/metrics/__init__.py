"""Metrics adapters package providing in-memory and Prometheus implementations."""

from hexastack_core.adapters.metrics.in_memory import (
    InMemoryMetricsAdapter,
    MetricRecord,
)

__all__ = [
    "InMemoryMetricsAdapter",
    "MetricRecord",
]
