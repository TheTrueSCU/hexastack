"""Unit tests for StrawberryMetricsExtension in hexastack_graphql."""

from __future__ import annotations

from unittest.mock import MagicMock

from hexastack_core.adapters.metrics import InMemoryMetricsAdapter
from hexastack_graphql.adapters.metrics import StrawberryMetricsExtension


def test_strawberry_metrics_extension_records_metrics() -> None:
    """Verify StrawberryMetricsExtension measures and records GraphQL operations."""
    metrics = InMemoryMetricsAdapter()

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
