"""Unit tests for MetricsPort abstract interface."""

from __future__ import annotations

import inspect
from typing import Any

import pytest

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


def test_metrics_port_is_abstract() -> None:
    """Verify that MetricsPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(MetricsPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        MetricsPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_metrics_port_abstract_methods() -> None:
    """Verify abstract methods on MetricsPort."""
    expected = {
        "generate_metrics_text",
        "increment_counter",
        "record_histogram",
        "set_gauge",
    }
    abstracts = MetricsPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
