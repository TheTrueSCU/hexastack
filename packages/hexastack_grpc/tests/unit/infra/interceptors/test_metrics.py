"""Unit tests for MetricsServerInterceptor in hexastack_grpc."""

from __future__ import annotations

from typing import Any

import grpc

from hexastack_core.ports.metrics import MetricsPort
from hexastack_grpc.infra.interceptors.metrics import MetricsServerInterceptor


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


class MockCallDetails:
    def __init__(self, method: str) -> None:
        self.method = method
        self.invocation_metadata = ()


def test_metrics_server_interceptor_records_rpc_metrics() -> None:
    """Verify MetricsServerInterceptor intercepts unary RPC and records metrics."""
    metrics = MockMetrics()
    interceptor = MetricsServerInterceptor(metrics=metrics)

    def dummy_handler(request: Any, context: Any) -> str:
        return f"hello_{request}"

    original_rpc_handler = grpc.unary_unary_rpc_method_handler(dummy_handler)

    def continuation(call_details: Any) -> grpc.RpcMethodHandler:
        return original_rpc_handler

    details = MockCallDetails(method="/UserService/GetUser")
    wrapped_handler: Any = interceptor.intercept_service(continuation, details)

    res = wrapped_handler.unary_unary("world", None)
    assert res == "hello_world"

    assert len(metrics.counters) == 1
    assert metrics.counters[0]["name"] == "grpc_server_handled_total"
    assert metrics.counters[0]["labels"]["grpc_service"] == "UserService"
    assert metrics.counters[0]["labels"]["grpc_method"] == "GetUser"
    assert metrics.counters[0]["labels"]["grpc_code"] == "OK"

    assert len(metrics.histograms) == 1
    assert metrics.histograms[0]["name"] == "grpc_server_handling_seconds"
    assert metrics.histograms[0]["labels"]["grpc_service"] == "UserService"
