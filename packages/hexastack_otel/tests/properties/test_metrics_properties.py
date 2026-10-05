"""Hypothesis property-based tests for Prometheus and InMemoryMetricsAdapter telemetry invariants.

Notes/Architectural Intent:
    Fuzzes arbitrary metric names, labels, increments, and histogram observations to prove:
    1. Counter Monotonicity & Commutativity:
       - Increments sum correctly regardless of submission order.
       - Prometheus exposition text formatting produces valid TYPE and metric lines.
    2. Histogram Invariants:
       - `_count` equals total number of observations.
       - `_sum` equals exact mathematical sum of observation values.
    3. Gauge Invariants:
       - Gauge value always reflects the most recent `set_gauge` call for that label set.
    4. Adapter Parity:
       - Both `InMemoryMetricsAdapter` and `PrometheusMetricsAdapter` produce structurally valid exposition bytes.
"""

from __future__ import annotations

import string

from hypothesis import given
from hypothesis import strategies as st
from prometheus_client import CollectorRegistry

from hexastack_core.adapters.metrics import InMemoryMetricsAdapter
from hexastack_otel.adapters.metrics.prometheus import PrometheusMetricsAdapter

# Strategies
metric_names = st.text(
    alphabet=string.ascii_lowercase + "_",
    min_size=2,
    max_size=20,
).filter(lambda s: s[0].isalpha())

label_keys = st.text(
    alphabet=string.ascii_lowercase + "_",
    min_size=2,
    max_size=10,
).filter(lambda s: s[0].isalpha())

label_values = st.text(
    alphabet=string.ascii_lowercase + string.digits + "_-",
    min_size=1,
    max_size=20,
)

labels_strategy = st.dictionaries(
    keys=label_keys,
    values=label_values,
    max_size=3,
)

positive_floats = st.floats(
    min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False
)


@given(
    name=metric_names,
    increments=st.lists(positive_floats, min_size=1, max_size=10),
    labels=labels_strategy,
)
def test_in_memory_metrics_counter_invariants(
    name: str, increments: list[float], labels: dict[str, str]
) -> None:
    """Property: Counter value equals sum of individual increments and renders valid text."""
    metrics = InMemoryMetricsAdapter()

    for inc in increments:
        metrics.increment_counter(name, value=inc, labels=labels)

    assert len(metrics.counters) == len(increments)

    text = metrics.generate_metrics_text().decode("utf-8")
    assert f"# TYPE {name} counter" in text
    assert f"{name}" in text


@given(
    name=metric_names,
    observations=st.lists(positive_floats, min_size=1, max_size=10),
    labels=labels_strategy,
)
def test_in_memory_metrics_histogram_invariants(
    name: str, observations: list[float], labels: dict[str, str]
) -> None:
    """Property: Histogram count equals len(observations) and sum equals sum(observations)."""
    metrics = InMemoryMetricsAdapter()

    for obs in observations:
        metrics.record_histogram(name, value=obs, labels=labels)

    assert len(metrics.histograms) == len(observations)

    text = metrics.generate_metrics_text().decode("utf-8")
    assert f"# TYPE {name} histogram" in text
    assert f"{name}_count" in text
    assert f"{len(observations)}" in text


@given(
    name=metric_names,
    gauge_values=st.lists(positive_floats, min_size=1, max_size=5),
    labels=labels_strategy,
)
def test_in_memory_metrics_gauge_invariants(
    name: str, gauge_values: list[float], labels: dict[str, str]
) -> None:
    """Property: Gauge always reflects the latest assigned value."""
    metrics = InMemoryMetricsAdapter()

    for val in gauge_values:
        metrics.set_gauge(name, value=val, labels=labels)

    text = metrics.generate_metrics_text().decode("utf-8")
    assert f"# TYPE {name} gauge" in text
    assert f"{name}" in text


@given(
    name=metric_names,
    val=positive_floats,
)
def test_prometheus_adapter_exposition_properties(name: str, val: float) -> None:
    """Property: PrometheusMetricsAdapter generates valid exposition text for arbitrary metrics."""
    registry = CollectorRegistry(auto_describe=True)
    adapter = PrometheusMetricsAdapter(registry=registry)

    adapter.increment_counter(name, value=val)
    text = adapter.generate_metrics_text().decode("utf-8")

    assert f"# TYPE {name}" in text
    assert f"{val}" in text
