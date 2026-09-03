"""In-Memory MetricsPort Adapter for test inspection and zero-dependency collection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from hexastack_core.ports.metrics import MetricsPort


@dataclass(frozen=True)
class MetricRecord:
    """Immutable record capturing a single metric measurement.

    Notes/Architectural Intent:
        Preserves metric invocation parameters for test assertions and telemetry replay.
    """

    metric_type: str
    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    description: str = ""


class InMemoryMetricsAdapter(MetricsPort):
    """In-memory thread-safe metrics adapter capturing measurements for test assertions.

    Notes/Architectural Intent:
        Provides canonical in-memory metrics storage across all Hexastack presentation
        adapters (FastAPI, gRPC, GraphQL, MCP, OTEL) without external Prometheus
        client dependencies.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory metrics storage."""
        self._lock = Lock()
        self._records: list[MetricRecord] = []
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._histograms: dict[
            tuple[str, tuple[tuple[str, str], ...]], list[float]
        ] = {}

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Mapping[str, str] | None = None,
        description: str = "",
    ) -> None:
        """Increment an in-memory counter metric.

        Args:
            name: Metric identifier string.
            value: Increment value (default 1.0).
            labels: Key-value label dimensions.
            description: Informative description of the metric.
        """
        normalized_labels = dict(labels) if labels else {}
        key = (name, tuple(sorted(normalized_labels.items())))
        with self._lock:
            self._records.append(
                MetricRecord(
                    metric_type="counter",
                    name=name,
                    value=value,
                    labels=normalized_labels,
                    description=description,
                )
            )
            self._counters[key] = self._counters.get(key, 0.0) + value

    def record_histogram(
        self,
        name: str,
        value: float,
        labels: Mapping[str, str] | None = None,
        description: str = "",
    ) -> None:
        """Record an observation in an in-memory histogram distribution.

        Args:
            name: Metric identifier string.
            value: Observed value.
            labels: Key-value label dimensions.
            description: Informative description of the metric.
        """
        normalized_labels = dict(labels) if labels else {}
        key = (name, tuple(sorted(normalized_labels.items())))
        with self._lock:
            self._records.append(
                MetricRecord(
                    metric_type="histogram",
                    name=name,
                    value=value,
                    labels=normalized_labels,
                    description=description,
                )
            )
            self._histograms.setdefault(key, []).append(value)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Mapping[str, str] | None = None,
        description: str = "",
    ) -> None:
        """Set the current value of an in-memory gauge metric.

        Args:
            name: Metric identifier string.
            value: Current gauge value.
            labels: Key-value label dimensions.
            description: Informative description of the metric.
        """
        normalized_labels = dict(labels) if labels else {}
        key = (name, tuple(sorted(normalized_labels.items())))
        with self._lock:
            self._records.append(
                MetricRecord(
                    metric_type="gauge",
                    name=name,
                    value=value,
                    labels=normalized_labels,
                    description=description,
                )
            )
            self._gauges[key] = value

    def generate_metrics_text(self) -> bytes:
        """Generate Prometheus-compatible text representation of captured metrics.

        Returns:
            Prometheus text exposition format encoded as bytes.
        """
        lines: list[str] = []
        with self._lock:
            for (name, label_items), val in sorted(self._counters.items()):
                label_str = (
                    "{" + ",".join(f'{k}="{v}"' for k, v in label_items) + "}"
                    if label_items
                    else ""
                )
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name}{label_str} {val}")

            for (name, label_items), val in sorted(self._gauges.items()):
                label_str = (
                    "{" + ",".join(f'{k}="{v}"' for k, v in label_items) + "}"
                    if label_items
                    else ""
                )
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name}{label_str} {val}")

            for (name, label_items), observations in sorted(self._histograms.items()):
                label_str = (
                    "{" + ",".join(f'{k}="{v}"' for k, v in label_items) + "}"
                    if label_items
                    else ""
                )
                lines.append(f"# TYPE {name} histogram")
                lines.append(f"{name}_count{label_str} {len(observations)}")
                lines.append(f"{name}_sum{label_str} {sum(observations)}")

        return "\n".join(lines).encode("utf-8") + b"\n"

    @property
    def records(self) -> list[MetricRecord]:
        """Retrieve all recorded metric events."""
        with self._lock:
            return list(self._records)

    @property
    def counters(self) -> list[dict[str, Any]]:
        """Retrieve counter events formatted for backwards-compatible test assertions."""
        with self._lock:
            return [
                {"name": r.name, "value": r.value, "labels": r.labels}
                for r in self._records
                if r.metric_type == "counter"
            ]

    @property
    def histograms(self) -> list[dict[str, Any]]:
        """Retrieve histogram events formatted for backwards-compatible test assertions."""
        with self._lock:
            return [
                {"name": r.name, "value": r.value, "labels": r.labels}
                for r in self._records
                if r.metric_type == "histogram"
            ]

    @property
    def gauges(self) -> list[dict[str, Any]]:
        """Retrieve gauge events formatted for backwards-compatible test assertions."""
        with self._lock:
            return [
                {"name": r.name, "value": r.value, "labels": r.labels}
                for r in self._records
                if r.metric_type == "gauge"
            ]

    def clear(self) -> None:
        """Clear all stored metric records and aggregated values."""
        with self._lock:
            self._records.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


__all__ = [
    "InMemoryMetricsAdapter",
    "MetricRecord",
]
