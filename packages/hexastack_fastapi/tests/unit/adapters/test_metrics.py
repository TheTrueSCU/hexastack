"""Unit tests for create_metrics_router in hexastack_fastapi."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_core.adapters.metrics import InMemoryMetricsAdapter
from hexastack_core.ports.metrics import MetricsPort
from hexastack_fastapi.adapters.metrics import create_metrics_router


def test_metrics_endpoint_with_container() -> None:
    """Verify /metrics route returns formatted Prometheus metrics."""
    metrics = InMemoryMetricsAdapter()
    metrics.increment_counter("test_metric", 42.0)

    container = Container()
    container.add_instance(metrics, declared_class=MetricsPort)

    app = FastAPI()
    router = create_metrics_router(container=container)
    app.include_router(router)

    client = TestClient(app)
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "test_metric 42.0" in res.text
