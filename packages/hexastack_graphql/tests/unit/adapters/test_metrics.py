"""Unit tests for StrawberryMetricsExtension in hexastack_graphql."""

from __future__ import annotations

from unittest.mock import MagicMock

from hexastack_core.ports.metrics import MetricsPort
from hexastack_graphql.adapters.metrics import StrawberryMetricsExtension


class MockMetrics(MetricsPort):
    def __init__(self) -> None:
        self.counters: list[dict] = []
        self.histograms: list[dict] = []

    def increment_counter(
        self, name: str, value: float = 1.0, labels=None, description: str = ""
    ) -> None:
        self.counters.append({"name": name, "value": value, "labels": labels})

    def record_histogram(
        self, name: str, value: float, labels=None, description: str = ""
    ) -> None:
        self.histograms.append({"name": name, "value": value, "labels": labels})

    def set_gauge(
        self, name: str, value: float, labels=None, description: str = ""
    ) -> None:
        pass

    def generate_metrics_text(self) -> bytes:
        return b"# mock"


def test_strawberry_metrics_extension_records_metrics() -> None:
    """Verify StrawberryMetricsExtension measures and records GraphQL operations."""
    metrics = MockMetrics()
    ctx = MagicMock()
    ctx.operation_name = "GetUsersQuery"
    ctx.query = "{ users { id name } }"

    import contextlib

    ext = StrawberryMetricsExtension(metrics=metrics, execution_context=ctx)
    gen = ext.on_operation()
    next(gen)
    with contextlib.suppress(StopIteration):
        next(gen)

    assert len(metrics.counters) == 1

    assert metrics.counters[0]["name"] == "graphql_operations_total"
    assert metrics.counters[0]["labels"]["operation"] == "GetUsersQuery"

    assert len(metrics.histograms) == 1
    assert metrics.histograms[0]["name"] == "graphql_operation_duration_seconds"
