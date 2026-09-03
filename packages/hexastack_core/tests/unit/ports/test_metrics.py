"""Unit tests for MetricsPort abstract interface."""

from __future__ import annotations

from typing import Any

from hexastack_core.ports.metrics import MetricsPort


class DummyMetrics(MetricsPort):
    def increment_counter(
        self, name: str, value: float = 1.0, labels: Any = None, description: str = ""
    ) -> None:
        pass

    def record_histogram(
        self, name: str, value: float, labels: Any = None, description: str = ""
    ) -> None:
        pass

    def set_gauge(
        self, name: str, value: float, labels: Any = None, description: str = ""
    ) -> None:
        pass

    def generate_metrics_text(self) -> bytes:
        return b"# metrics"


def test_metrics_port_instantiation() -> None:
    """Verify MetricsPort concrete implementation satisfies interface."""
    adapter = DummyMetrics()
    assert adapter.generate_metrics_text() == b"# metrics"
