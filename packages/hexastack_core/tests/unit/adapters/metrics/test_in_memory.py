"""Unit tests for InMemoryMetricsAdapter."""

from __future__ import annotations

from hexastack_core.adapters.metrics.in_memory import (
    InMemoryMetricsAdapter,
)


def test_in_memory_metrics_counter_recording() -> None:
    """Verify counter metric recording and aggregation."""
    metrics = InMemoryMetricsAdapter()
    metrics.increment_counter(
        "http_requests_total", 1.0, {"method": "GET", "status": "200"}
    )
    metrics.increment_counter(
        "http_requests_total", 2.0, {"method": "GET", "status": "200"}
    )
    metrics.increment_counter(
        "http_requests_total", 1.0, {"method": "POST", "status": "201"}
    )

    assert len(metrics.records) == 3
    assert len(metrics.counters) == 3

    text = metrics.generate_metrics_text().decode("utf-8")
    assert 'http_requests_total{method="GET",status="200"} 3.0' in text
    assert 'http_requests_total{method="POST",status="201"} 1.0' in text


def test_in_memory_metrics_histogram_and_gauge() -> None:
    """Verify histogram and gauge metric recording."""
    metrics = InMemoryMetricsAdapter()
    metrics.record_histogram("request_latency_seconds", 0.05, {"handler": "get_user"})
    metrics.record_histogram("request_latency_seconds", 0.15, {"handler": "get_user"})
    metrics.set_gauge("active_connections", 10.0)

    assert len(metrics.histograms) == 2
    assert len(metrics.gauges) == 1

    text = metrics.generate_metrics_text().decode("utf-8")
    assert 'request_latency_seconds_count{handler="get_user"} 2' in text
    assert 'request_latency_seconds_sum{handler="get_user"} 0.2' in text
    assert "active_connections 10.0" in text

    metrics.clear()
    assert len(metrics.records) == 0
    assert len(metrics.counters) == 0
    assert len(metrics.histograms) == 0
    assert len(metrics.gauges) == 0
