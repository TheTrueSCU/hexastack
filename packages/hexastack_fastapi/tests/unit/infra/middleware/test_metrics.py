"""Unit tests for HttpMetricsMiddleware."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_core.adapters.metrics import InMemoryMetricsAdapter
from hexastack_core.ports.metrics import MetricsPort
from hexastack_fastapi.infra.middleware.metrics import HttpMetricsMiddleware


def test_http_metrics_middleware_captures_red_metrics() -> None:
    """Verify HttpMetricsMiddleware records counter and histogram for requests."""
    metrics = InMemoryMetricsAdapter()

    container = Container()
    container.add_instance(metrics, declared_class=MetricsPort)

    app = FastAPI()
    app.add_middleware(HttpMetricsMiddleware, container=container)

    @app.get("/items/{item_id}")
    async def get_item(item_id: str):
        return {"id": item_id}

    client = TestClient(app)
    res = client.get("/items/42")
    assert res.status_code == 200

    assert len(metrics.counters) == 1
    assert metrics.counters[0]["name"] == "http_requests_total"
    assert metrics.counters[0]["labels"]["method"] == "GET"
    assert metrics.counters[0]["labels"]["status_code"] == "200"

    assert len(metrics.histograms) == 1
    assert metrics.histograms[0]["name"] == "http_request_duration_seconds"
    assert metrics.histograms[0]["labels"]["method"] == "GET"
