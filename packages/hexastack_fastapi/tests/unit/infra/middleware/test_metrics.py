"""Unit tests for HttpMetricsMiddleware."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_core.ports.metrics import MetricsPort
from hexastack_fastapi.infra.middleware.metrics import HttpMetricsMiddleware


class MockMetrics(MetricsPort):
    def __init__(self) -> None:
        self.counters: list[dict] = []
        self.histograms: list[dict] = []

    def increment_counter(
        self, name: str, value: float = 1.0, labels=None, description: str = ""
    ) -> None:
        self.counters.append({"name": name, "value": value, "labels": labels})

    def record_histogram(
        self, name: str, value: float, labels=None, description: str = ""
    ) -> None:
        self.histograms.append({"name": name, "value": value, "labels": labels})

    def set_gauge(
        self, name: str, value: float, labels=None, description: str = ""
    ) -> None:
        pass

    def generate_metrics_text(self) -> bytes:
        return b"# mock"


def test_http_metrics_middleware_captures_red_metrics() -> None:
    """Verify HttpMetricsMiddleware records counter and histogram for requests."""
    metrics = MockMetrics()
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
