"""Unit tests for McpMetricsMiddleware in hexastack_mcp."""

from __future__ import annotations

import pytest

from hexastack_core.ports.metrics import MetricsPort
from hexastack_mcp.infra.middleware.metrics import McpMetricsMiddleware


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


@pytest.mark.anyio
async def test_mcp_metrics_middleware_records_tool_metrics() -> None:
    """Verify McpMetricsMiddleware records tool execution metrics."""
    metrics = MockMetrics()
    mw = McpMetricsMiddleware(metrics=metrics)

    async def sample_tool(param: str) -> str:
        return f"result_{param}"

    res = await mw("search_kb", sample_tool, param="ai")
    assert res == "result_ai"

    assert len(metrics.counters) == 1
    assert metrics.counters[0]["name"] == "mcp_tools_total"
    assert metrics.counters[0]["labels"]["tool"] == "search_kb"
    assert metrics.counters[0]["labels"]["status"] == "success"

    assert len(metrics.histograms) == 1
    assert metrics.histograms[0]["name"] == "mcp_tool_duration_seconds"
