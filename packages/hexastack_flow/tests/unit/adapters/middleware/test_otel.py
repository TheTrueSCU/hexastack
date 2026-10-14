"""Unit tests for OtelStepMiddleware."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from hexaflow.domain.state import StepContext
from hexaflow.dsl import Workflow

from hexastack_core.exceptions import MissingDependencyError
from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_flow.adapters.cqrs.runner import CqrsWorkflowRunner
from hexastack_flow.adapters.middleware.otel import OtelStepMiddleware
from hexastack_flow.infra.bootstrap import FlowBootstrapper
from hexastack_flow.ports.orchestrator import CqrsWorkflowOrchestratorPort
from hexastack_otel.adapters.tracing.in_memory import InMemoryTracingAdapter
from hexastack_otel.ports.tracing import TracingPort


def test_otel_step_middleware_init_with_tracer() -> None:
    """Verify initialization stores the provided tracer."""
    tracer = InMemoryTracingAdapter()
    middleware = OtelStepMiddleware(tracer=tracer)
    assert middleware._tracer is tracer


def test_otel_step_middleware_init_resolves_default_tracer() -> None:
    """Verify initialization resolves default tracer when none provided."""
    with patch("hexastack_otel.adapters.tracing.otel.OtelTracingAdapter") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        middleware = OtelStepMiddleware()
        assert middleware._tracer is mock_instance


def test_otel_step_middleware_missing_dependency() -> None:
    """Verify MissingDependencyError raised when hexastack-otel is absent."""
    with (
        patch(
            "hexastack_flow.adapters.middleware.otel.require_dependency",
            side_effect=MissingDependencyError("hexastack-otel missing"),
        ),
        pytest.raises(MissingDependencyError, match="hexastack-otel missing"),
    ):
        OtelStepMiddleware()


def test_otel_step_middleware_sync_step_success() -> None:
    """Verify span attributes and OK status for successful synchronous step."""
    tracer = InMemoryTracingAdapter()
    middleware = OtelStepMiddleware(tracer=tracer)

    ctx = StepContext(
        run_id="run-123",
        stage_name="processing",
        step_name="charge_card",
        attempt_number=1,
    )

    def next_action(c: StepContext) -> dict[str, str]:
        return {"status": "success"}

    res = middleware(ctx, next_action)
    assert res == {"status": "success"}

    finished = tracer.finished_spans
    assert len(finished) == 1

    span = finished[0]
    assert span.name == "workflow.step.charge_card"
    assert span.status == "OK"
    assert span.attributes["workflow.run_id"] == "run-123"
    assert span.attributes["workflow.stage"] == "processing"
    assert span.attributes["workflow.step"] == "charge_card"
    assert span.attributes["workflow.attempt"] == 1


@pytest.mark.asyncio
async def test_otel_step_middleware_async_step_success() -> None:
    """Verify span lifecycle for successful asynchronous step."""
    tracer = InMemoryTracingAdapter()
    middleware = OtelStepMiddleware(tracer=tracer)

    ctx = StepContext(
        run_id="run-456",
        stage_name="fulfillment",
        step_name="ship_package",
        attempt_number=2,
    )

    async def async_next_action(c: StepContext) -> str:
        return "tracking-xyz"

    coro = middleware(ctx, async_next_action)
    res = await coro
    assert res == "tracking-xyz"

    finished = tracer.finished_spans
    assert len(finished) == 1

    span = finished[0]
    assert span.name == "workflow.step.ship_package"
    assert span.status == "OK"
    assert span.attributes["workflow.attempt"] == 2


def test_otel_step_middleware_sync_step_error() -> None:
    """Verify exception recording and ERROR status on failure."""
    tracer = InMemoryTracingAdapter()
    middleware = OtelStepMiddleware(tracer=tracer)

    ctx = StepContext(
        run_id="run-err",
        stage_name="validation",
        step_name="check_funds",
        attempt_number=1,
    )

    def failing_action(c: StepContext) -> None:
        raise ValueError("Insufficient funds")

    raised = False
    try:
        middleware(ctx, failing_action)
    except ValueError as exc:
        raised = True
        err_msg = str(exc)
        assert "Insufficient funds" in err_msg
    assert raised is True

    finished = tracer.finished_spans
    assert len(finished) == 1

    span = finished[0]
    assert span.name == "workflow.step.check_funds"
    assert span.status == "ERROR"
    assert len(span.exceptions) == 1
    assert str(span.exceptions[0]) == "Insufficient funds"


@pytest.mark.asyncio
async def test_otel_step_middleware_async_step_error() -> None:
    """Verify async exception recording and status on failure."""
    tracer = InMemoryTracingAdapter()
    middleware = OtelStepMiddleware(tracer=tracer)

    ctx = StepContext(
        run_id="run-async-err",
        stage_name="network",
        step_name="call_gateway",
        attempt_number=3,
    )

    async def failing_async(c: StepContext) -> None:
        raise ConnectionError("Gateway timeout")

    coro = middleware(ctx, failing_async)
    raised = False
    try:
        _ = await coro
    except ConnectionError as exc:
        raised = True
        err_msg = str(exc)
        assert "Gateway timeout" in err_msg
    assert raised is True

    finished = tracer.finished_spans
    assert len(finished) == 1

    span = finished[0]
    assert span.name == "workflow.step.call_gateway"
    assert span.status == "ERROR"
    assert len(span.exceptions) == 1


def test_otel_step_middleware_integration_with_workflow() -> None:
    """Verify integration of OtelStepMiddleware with CqrsWorkflowRunner."""
    tracer = InMemoryTracingAdapter()
    middleware = OtelStepMiddleware(tracer=tracer)
    runner = CqrsWorkflowRunner(middleware=[middleware])

    wf = Workflow(name="checkout", version="1.0.0")

    @wf.stage("cart")
    @wf.step("verify_items")
    def verify_items(ctx: Any) -> dict[str, bool]:
        return {"ok": True}

    @wf.stage("payment")
    @wf.step("process_card", depends_on=["verify_items"])
    def process_card(ctx: Any) -> dict[str, str]:
        return {"payment_id": "pay-1"}

    result = runner.execute(wf)
    assert result.status == "COMPLETED"

    finished = tracer.finished_spans
    assert len(finished) == 2

    step_names = [s.attributes["workflow.step"] for s in finished]
    assert "verify_items" in step_names
    assert "process_card" in step_names


def test_flow_bootstrapper_wires_otel_middleware() -> None:
    """Verify FlowBootstrapper resolves TracingPort and injects OtelStepMiddleware."""
    tracer = InMemoryTracingAdapter()

    container: dict[type, Any] = {
        TracingPort: tracer,
    }

    mock_di = MagicMock()
    mock_di.__contains__.side_effect = lambda key: key in container
    mock_di.resolve.side_effect = lambda key: container[key]

    from hexastack_core.infra.registries.config import ConfigRegistry

    context = BootstrapContext(
        container=mock_di,
        config=None,
        config_registry=ConfigRegistry(),
        properties={},
    )
    bootstrapper = FlowBootstrapper()
    bootstrapper.configure(context)

    runner = context.properties.get("flow_runner")
    assert isinstance(runner, CqrsWorkflowRunner)

    added_calls = mock_di.add_instance.call_args_list
    assert len(added_calls) == 1

    instance_arg = added_calls[0][0][0]
    declared_arg = added_calls[0][1]["declared_class"]
    assert instance_arg is runner
    assert declared_arg is CqrsWorkflowOrchestratorPort
