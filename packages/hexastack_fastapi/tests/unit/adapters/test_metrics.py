"""Unit tests for create_metrics_router in hexastack_fastapi."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_core.ports.metrics import MetricsPort
from hexastack_fastapi.adapters.metrics import create_metrics_router


class DummyMetrics(MetricsPort):
    def increment_counter(
        self, name: str, value: float = 1.0, labels=None, description: str = ""
    ) -> None:
        pass

    def record_histogram(
        self, name: str, value: float, labels=None, description: str = ""
    ) -> None:
        pass

    def set_gauge(
        self, name: str, value: float, labels=None, description: str = ""
    ) -> None:
        pass

    def generate_metrics_text(self) -> bytes:
        return (
            b"# HELP test_metric Test\n# TYPE test_metric counter\ntest_metric 42.0\n"
        )


def test_metrics_endpoint_with_container() -> None:
    """Verify /metrics route returns formatted Prometheus metrics."""
    container = Container()
    container.add_instance(DummyMetrics(), declared_class=MetricsPort)

    app = FastAPI()
    router = create_metrics_router(container=container)
    app.include_router(router)

    client = TestClient(app)
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "test_metric 42.0" in res.text
