"""Prometheus MetricsPort Adapter."""

from __future__ import annotations

from collections.abc import Mapping

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from hexastack_core.ports.metrics import MetricsPort


class PrometheusMetricsAdapter(MetricsPort):
    """MetricsPort implementation backed by the official prometheus_client library.

    Notes/Architectural Intent:
        Thread-safe Prometheus registry caching dynamic Counter, Gauge, and Histogram metrics.
        Produces standard Prometheus text exposition format via generate_metrics_text().
    """

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """Initialize PrometheusMetricsAdapter.

        Args:
            registry: Optional CollectorRegistry. If None, creates an isolated CollectorRegistry.
        """
        self.registry = registry or CollectorRegistry(auto_describe=True)
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Mapping[str, str] | None = None,
        description: str = "",
    ) -> None:
        """Increment a Prometheus counter metric."""
        label_names = sorted(labels.keys()) if labels else []
        if name not in self._counters:
            self._counters[name] = Counter(
                name,
                description or name,
                labelnames=label_names,
                registry=self.registry,
            )
        counter = self._counters[name]
        if labels:
            counter.labels(**labels).inc(value)
        else:
            counter.inc(value)

    def record_histogram(
        self,
        name: str,
        value: float,
        labels: Mapping[str, str] | None = None,
        description: str = "",
    ) -> None:
        """Record an observation in a Prometheus histogram metric."""
        label_names = sorted(labels.keys()) if labels else []
        if name not in self._histograms:
            self._histograms[name] = Histogram(
                name,
                description or name,
                labelnames=label_names,
                registry=self.registry,
            )
        histogram = self._histograms[name]
        if labels:
            histogram.labels(**labels).observe(value)
        else:
            histogram.observe(value)

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Mapping[str, str] | None = None,
        description: str = "",
    ) -> None:
        """Set a Prometheus gauge metric value."""
        label_names = sorted(labels.keys()) if labels else []
        if name not in self._gauges:
            self._gauges[name] = Gauge(
                name,
                description or name,
                labelnames=label_names,
                registry=self.registry,
            )
        gauge = self._gauges[name]
        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)

    def generate_metrics_text(self) -> bytes:
        """Generate Prometheus exposition text representation."""
        return generate_latest(self.registry)


__all__ = [
    "PrometheusMetricsAdapter",
]
