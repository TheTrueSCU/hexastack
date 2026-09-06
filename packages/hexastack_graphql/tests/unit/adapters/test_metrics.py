"""Unit tests for StrawberryMetricsExtension in hexastack_graphql."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock

from hexastack_core.adapters.feature_flags import InMemoryFeatureFlagAdapter
from hexastack_core.adapters.metrics import InMemoryMetricsAdapter
from hexastack_graphql.adapters.metrics import StrawberryMetricsExtension


def test_strawberry_metrics_extension_records_metrics() -> None:
    """Verify StrawberryMetricsExtension measures and records GraphQL operations."""
    metrics = InMemoryMetricsAdapter()

    ctx = MagicMock()
    ctx.operation_name = "GetUsersQuery"
    ctx.query = "{ users { id name } }"

    ext = StrawberryMetricsExtension(metrics=metrics, execution_context=ctx)
    gen = ext.on_operation()
    next(gen)
    with contextlib.suppress(StopIteration):
        next(gen)

    assert len(metrics.counters) == 1
    assert metrics.counters[0]["name"] == "graphql_operations_total"
    assert metrics.counters[0]["value"] == 1.0
    assert metrics.counters[0]["labels"] == {"operation": "GetUsersQuery"}

    # Inspect records for description
    counter_record = metrics.records[0]
    assert counter_record.description == "Total GraphQL operations processed"

    assert len(metrics.histograms) == 1
    assert metrics.histograms[0]["name"] == "graphql_operation_duration_seconds"
    assert metrics.histograms[0]["value"] >= 0.0
    assert metrics.histograms[0]["labels"] == {"operation": "GetUsersQuery"}
    histo_record = metrics.records[1]
    assert (
        histo_record.description == "GraphQL operation duration distribution in seconds"
    )


def test_strawberry_metrics_extension_query_substring_fallback() -> None:
    """Verify StrawberryMetricsExtension falls back to query substring [:30] when operation_name is None."""
    metrics = InMemoryMetricsAdapter()

    ctx = MagicMock()
    ctx.operation_name = None
    ctx.query = "query LongQueryNameThatExceedsThirtyCharacters { field }"

    ext = StrawberryMetricsExtension(metrics=metrics, execution_context=ctx)
    gen = ext.on_operation()
    next(gen)
    with contextlib.suppress(StopIteration):
        next(gen)

    expected_op = "query LongQueryNameThatExceeds"
    assert metrics.counters[0]["labels"]["operation"] == expected_op
    assert metrics.histograms[0]["labels"]["operation"] == expected_op


def test_strawberry_metrics_extension_anonymous_fallback() -> None:
    """Verify StrawberryMetricsExtension falls back to 'anonymous' when operation_name and query are empty."""
    metrics = InMemoryMetricsAdapter()

    ctx = MagicMock()
    ctx.operation_name = None
    ctx.query = None

    ext = StrawberryMetricsExtension(metrics=metrics, execution_context=ctx)
    gen = ext.on_operation()
    next(gen)
    with contextlib.suppress(StopIteration):
        next(gen)

    assert metrics.counters[0]["labels"]["operation"] == "anonymous"
    assert metrics.histograms[0]["labels"]["operation"] == "anonymous"


def test_strawberry_metrics_extension_none_metrics() -> None:
    """Verify StrawberryMetricsExtension safely exits when metrics port is None."""
    ctx = MagicMock()
    ctx.operation_name = "Test"
    ext = StrawberryMetricsExtension(metrics=None, execution_context=ctx)
    gen = ext.on_operation()
    next(gen)
    with contextlib.suppress(StopIteration):
        next(gen)


def test_strawberry_metrics_extension_feature_flags() -> None:
    """Verify StrawberryMetricsExtension respects FeatureFlagPort evaluation."""
    metrics = InMemoryMetricsAdapter()
    flags = InMemoryFeatureFlagAdapter()

    ctx = MagicMock()
    ctx.operation_name = "Test"

    # Flag enabled by default
    ext = StrawberryMetricsExtension(
        metrics=metrics, flags=flags, execution_context=ctx
    )
    gen = ext.on_operation()
    next(gen)
    with contextlib.suppress(StopIteration):
        next(gen)
    assert len(metrics.counters) == 1

    # Disable flag
    metrics.clear()
    flags.set_flag("features.metrics.graphql", False)
    ext2 = StrawberryMetricsExtension(
        metrics=metrics, flags=flags, execution_context=ctx
    )
    gen2 = ext2.on_operation()
    next(gen2)
    with contextlib.suppress(StopIteration):
        next(gen2)
    assert len(metrics.counters) == 0
