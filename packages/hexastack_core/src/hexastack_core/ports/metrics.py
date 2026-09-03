"""Metrics and Telemetry Counter/Histogram Port Interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping


class MetricsPort(ABC):
    """Abstract port contract for collecting system and application metrics.

    Notes/Architectural Intent:
        Decouples metrics instrumentation from specific backends (Prometheus, OTel Metrics, In-Memory).
    """

    @abstractmethod
    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Mapping[str, str] | None = None,
        description: str = "",
    ) -> None:
        """Increment a monotonically increasing counter metric.

        Args:
            name: Metric identifier string (e.g. 'cqrs_commands_total').
            value: Increment value (default 1.0).
            labels: Key-value label dimensions for the metric.
            description: Informative description of the metric.
        """

    @abstractmethod
    def record_histogram(
        self,
        name: str,
        value: float,
        labels: Mapping[str, str] | None = None,
        description: str = "",
    ) -> None:
        """Record an observation in a distribution histogram metric (e.g. latency).

        Args:
            name: Metric identifier string (e.g. 'cqrs_execution_duration_seconds').
            value: Observed value (e.g. execution duration in seconds).
            labels: Key-value label dimensions.
            description: Informative description of the metric.
        """

    @abstractmethod
    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Mapping[str, str] | None = None,
        description: str = "",
    ) -> None:
        """Set the current value of a gauge metric.

        Args:
            name: Metric identifier string (e.g. 'active_connections').
            value: Current numerical value.
            labels: Key-value label dimensions.
            description: Informative description of the metric.
        """

    @abstractmethod
    def generate_metrics_text(self) -> bytes:
        """Generate formatted Prometheus exposition text format representation.

        Returns:
            Formatted metrics bytes ready for HTTP /metrics endpoint response.
        """


__all__ = [
    "MetricsPort",
]
