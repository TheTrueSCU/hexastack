"""Unit tests for PrometheusMetricsAdapter."""

from __future__ import annotations

from hexastack_otel.adapters.metrics.prometheus import PrometheusMetricsAdapter


def test_prometheus_metrics_adapter_counter_histogram_gauge() -> None:
    """Verify PrometheusMetricsAdapter collects metrics and outputs Prometheus text format."""
    adapter = PrometheusMetricsAdapter()

    # Counter
    adapter.increment_counter(
        "cqrs_commands_total", value=1, labels={"command": "CreateOrder"}
    )
    adapter.increment_counter(
        "cqrs_commands_total", value=2, labels={"command": "CreateOrder"}
    )

    # Gauge
    adapter.set_gauge("active_tasks_gauge", value=5, labels={"pool": "default"})

    # Histogram
    adapter.record_histogram(
        "cqrs_duration_seconds", value=0.045, labels={"command": "CreateOrder"}
    )

    # Generate text
    raw = adapter.generate_metrics_text().decode("utf-8")
    assert 'cqrs_commands_total{command="CreateOrder"} 3.0' in raw
    assert 'active_tasks_gauge{pool="default"} 5.0' in raw
    assert "cqrs_duration_seconds_count" in raw
