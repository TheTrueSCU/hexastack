"""Unit tests for CqrsMetricsMiddleware in hexastack_otel."""

from __future__ import annotations

from dataclasses import dataclass

from hexastack_core.domain import Command
from hexastack_core.ports.metrics import MetricsPort
from hexastack_otel.infra.middleware_metrics import CqrsMetricsMiddleware


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


@dataclass(frozen=True)
class CreateOrderCommand(Command):
    order_id: str


def test_cqrs_metrics_middleware_success() -> None:
    """Verify CqrsMetricsMiddleware records success metrics."""
    metrics = MockMetrics()
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
    metrics = MockMetrics()
    mw = CqrsMetricsMiddleware(metrics=metrics)

    cmd = CreateOrderCommand(order_id="ord-2")
    ctx = mw.before(cmd)
    mw.on_error(cmd, ValueError("failed"), ctx)

    assert len(metrics.counters) == 1
    assert metrics.counters[0]["labels"]["status"] == "error"
