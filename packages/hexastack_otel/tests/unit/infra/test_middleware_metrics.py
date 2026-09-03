"""Unit tests for CqrsMetricsMiddleware in hexastack_otel."""

from __future__ import annotations

from dataclasses import dataclass

from hexastack_core.adapters.metrics import InMemoryMetricsAdapter
from hexastack_core.domain import Command
from hexastack_otel.infra.middleware_metrics import CqrsMetricsMiddleware


@dataclass(frozen=True)
class CreateOrderCommand(Command):
    order_id: str


def test_cqrs_metrics_middleware_success() -> None:
    """Verify CqrsMetricsMiddleware records success metrics."""
    metrics = InMemoryMetricsAdapter()
    mw = CqrsMetricsMiddleware(metrics=metrics)

    cmd = CreateOrderCommand(order_id="ord-1")
    ctx = mw.before(cmd)
    res = mw.after(cmd, "order-created", ctx)
    assert res == "order-created"

    assert len(metrics.counters) == 1
    assert metrics.counters[0]["name"] == "cqrs_messages_total"
    assert metrics.counters[0]["labels"]["name"] == "CreateOrderCommand"
    assert metrics.counters[0]["labels"]["status"] == "success"

    assert len(metrics.histograms) == 1
    assert metrics.histograms[0]["name"] == "cqrs_message_duration_seconds"


def test_cqrs_metrics_middleware_error() -> None:
    """Verify CqrsMetricsMiddleware records error metrics."""
    metrics = InMemoryMetricsAdapter()
    mw = CqrsMetricsMiddleware(metrics=metrics)

    cmd = CreateOrderCommand(order_id="ord-2")
    ctx = mw.before(cmd)
    mw.on_error(cmd, ValueError("failed"), ctx)

    assert len(metrics.counters) == 1
    assert metrics.counters[0]["labels"]["status"] == "error"
