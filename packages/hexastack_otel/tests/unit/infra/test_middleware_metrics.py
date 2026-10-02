"""Unit tests for CqrsMetricsMiddleware in hexastack_otel."""

from __future__ import annotations

from dataclasses import dataclass

from hexastack_core.adapters.metrics import InMemoryMetricsAdapter
from hexastack_core.domain import Command, Query
from hexastack_otel.infra.middleware_metrics import CqrsMetricsMiddleware


@dataclass(frozen=True)
class CreateOrderCommand(Command):
    order_id: str


class GetOrderQuery(Query):
    order_id: str


def test_cqrs_metrics_middleware_success() -> None:
    """Verify CqrsMetricsMiddleware records success metrics for commands and queries."""
    metrics = InMemoryMetricsAdapter()
    mw = CqrsMetricsMiddleware(metrics=metrics)

    cmd = CreateOrderCommand(order_id="ord-1")
    ctx = mw.before(cmd)
    assert ctx["active"] is True
    assert ctx["name"] == "CreateOrderCommand"
    assert ctx["type"] == "command"

    res = mw.after(cmd, "order-created", ctx)
    assert res == "order-created"

    assert len(metrics.counters) == 1
    assert metrics.counters[0]["name"] == "cqrs_messages_total"
    assert metrics.counters[0]["labels"]["name"] == "CreateOrderCommand"
    assert metrics.counters[0]["labels"]["type"] == "command"
    assert metrics.counters[0]["labels"]["status"] == "success"
    assert metrics.counters[0]["value"] == 1.0

    assert len(metrics.histograms) == 1
    assert metrics.histograms[0]["name"] == "cqrs_message_duration_seconds"
    assert metrics.histograms[0]["labels"]["name"] == "CreateOrderCommand"
    assert metrics.histograms[0]["labels"]["type"] == "command"

    # Query success
    qry = GetOrderQuery(order_id="ord-1")
    ctx_qry = mw.before(qry)
    assert ctx_qry["type"] == "query"
    mw.after(qry, {"data": 123}, ctx_qry)
    assert metrics.counters[1]["labels"]["type"] == "query"
    assert metrics.counters[1]["labels"]["status"] == "success"
    assert metrics.histograms[1]["labels"]["type"] == "query"


def test_cqrs_metrics_middleware_error() -> None:
    """Verify CqrsMetricsMiddleware records error metrics."""
    metrics = InMemoryMetricsAdapter()
    mw = CqrsMetricsMiddleware(metrics=metrics)

    cmd = CreateOrderCommand(order_id="ord-2")
    ctx = mw.before(cmd)
    mw.on_error(cmd, ValueError("failed"), ctx)

    assert len(metrics.counters) == 1
    assert metrics.counters[0]["name"] == "cqrs_messages_total"
    assert metrics.counters[0]["labels"]["name"] == "CreateOrderCommand"
    assert metrics.counters[0]["labels"]["type"] == "command"
    assert metrics.counters[0]["labels"]["status"] == "error"
    assert metrics.counters[0]["value"] == 1.0

    assert len(metrics.histograms) == 1
    assert metrics.histograms[0]["name"] == "cqrs_message_duration_seconds"
    assert metrics.histograms[0]["labels"]["name"] == "CreateOrderCommand"
    assert metrics.histograms[0]["labels"]["type"] == "command"


def test_cqrs_metrics_middleware_disabled_and_feature_flags() -> None:
    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )

    metrics = InMemoryMetricsAdapter()
    cmd = CreateOrderCommand(order_id="ord-3")

    # 1. Master disabled toggle
    mw_disabled = CqrsMetricsMiddleware(metrics=metrics, enabled=False)
    ctx_dis = mw_disabled.before(cmd)
    assert ctx_dis == {"active": False}
    assert mw_disabled.after(cmd, "res", ctx_dis) == "res"
    mw_disabled.on_error(cmd, RuntimeError("err"), ctx_dis)
    assert len(metrics.counters) == 0

    # 2. Feature flag disabled
    flags = InMemoryFeatureFlagAdapter({"features.metrics.cqrs": False})
    mw_flags = CqrsMetricsMiddleware(metrics=metrics, enabled=True, flags=flags)
    ctx_flag_dis = mw_flags.before(cmd)
    assert ctx_flag_dis == {"active": False}

    # 3. Feature flag enabled
    flags.set_flag("features.metrics.cqrs", True)
    ctx_flag_en = mw_flags.before(cmd)
    assert ctx_flag_en["active"] is True
