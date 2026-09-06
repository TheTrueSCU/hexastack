from prometheus_client import CollectorRegistry

from hexastack_otel.adapters.metrics.prometheus import PrometheusMetricsAdapter


def test_prometheus_metrics_adapter_counter_histogram_gauge() -> None:
    """Verify PrometheusMetricsAdapter collects metrics and outputs Prometheus text format."""
    reg = CollectorRegistry(auto_describe=True)
    adapter = PrometheusMetricsAdapter(registry=reg)
    assert adapter.registry is reg

    # Counter with custom description and default value=1.0
    adapter.increment_counter(
        "cqrs_commands_total",
        labels={"command": "CreateOrder"},
        description="Total CQRS commands",
    )
    adapter.increment_counter(
        "cqrs_commands_total", value=2.0, labels={"command": "CreateOrder"}
    )

    # Counter without labels and with default description (name)
    adapter.increment_counter("plain_counter_total")

    # Gauge with custom description and with default description
    adapter.set_gauge(
        "active_tasks_gauge",
        value=5.0,
        labels={"pool": "default"},
        description="Active background tasks",
    )
    adapter.set_gauge("plain_gauge", value=42.0)

    # Histogram with custom description and with default description
    adapter.record_histogram(
        "cqrs_duration_seconds",
        value=0.045,
        labels={"command": "CreateOrder"},
        description="Duration of CQRS commands",
    )
    adapter.record_histogram("plain_duration_seconds", value=1.5)

    # Generate text
    raw = adapter.generate_metrics_text().decode("utf-8")
    assert 'cqrs_commands_total{command="CreateOrder"} 3.0' in raw
    assert "# HELP cqrs_commands_total Total CQRS commands" in raw
    assert "plain_counter_total 1.0" in raw
    assert "# HELP plain_counter_total plain_counter_total" in raw
    assert 'active_tasks_gauge{pool="default"} 5.0' in raw
    assert "# HELP active_tasks_gauge Active background tasks" in raw
    assert "plain_gauge 42.0" in raw
    assert "# HELP plain_gauge plain_gauge" in raw
    assert "cqrs_duration_seconds_count" in raw
    assert "# HELP cqrs_duration_seconds Duration of CQRS commands" in raw
    assert "plain_duration_seconds_count 1.0" in raw
    assert "# HELP plain_duration_seconds plain_duration_seconds" in raw


def test_prometheus_metrics_adapter_default_registry() -> None:
    """Verify default isolated CollectorRegistry is created when registry=None."""
    adapter = PrometheusMetricsAdapter()
    assert adapter.registry is not None
    assert isinstance(adapter.registry, CollectorRegistry)
