"""Unit tests for CqrsWorkflowRunner adapter.

Notes/Architectural Intent:
    Tests execution, resumption, and abort flows of CqrsWorkflowRunner,
    verifying state-to-result mapping and event publication.
"""

from unittest.mock import MagicMock

from hexaflow.domain.models import StageDefinition, StepDefinition, WorkflowDefinition

from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_flow.adapters.cqrs.runner import CqrsWorkflowRunner
from hexastack_flow.domain.events import (
    WorkflowAbortedEvent,
    WorkflowCompletedEvent,
    WorkflowStartedEvent,
    WorkflowSuspendedEvent,
)


def test_runner_execute_success() -> None:
    """Validate full workflow execution through CqrsWorkflowRunner."""
    mock_event_bus = MagicMock(spec=EventBusPort)
    runner = CqrsWorkflowRunner(event_bus=mock_event_bus)

    wf = WorkflowDefinition(
        name="test_runner_flow",
        stages=(
            StageDefinition(
                name="stage_1",
                steps=(
                    StepDefinition(
                        name="step_a", action=lambda ctx: {"greeting": "hello"}
                    ),
                    StepDefinition(
                        name="step_b",
                        action=lambda ctx: {"reply": "world"},
                        depends_on=("step_a",),
                    ),
                ),
            ),
        ),
    )

    result = runner.execute(wf)

    status = result.status
    run_id = result.run_id
    completed = result.completed_steps
    outputs = result.outputs

    assert status == "COMPLETED"
    assert len(run_id) > 0
    assert completed == ("step_a", "step_b")
    assert outputs["step_a"] == {"greeting": "hello"}
    assert outputs["step_b"] == {"reply": "world"}

    # Verify event publications
    assert mock_event_bus.publish.call_count >= 2
    events_published = [call[0][0] for call in mock_event_bus.publish.call_args_list]

    started_events = [
        e for e in events_published if isinstance(e, WorkflowStartedEvent)
    ]
    completed_events = [
        e for e in events_published if isinstance(e, WorkflowCompletedEvent)
    ]

    assert len(started_events) == 1
    assert len(completed_events) == 1
    assert completed_events[0].total_steps == 2


def test_runner_suspension_and_resume() -> None:
    """Validate workflow suspension on permanent failure and subsequent resumption."""
    mock_event_bus = MagicMock(spec=EventBusPort)
    runner = CqrsWorkflowRunner(event_bus=mock_event_bus)

    should_fail = True

    def _flaky_step(ctx) -> str:
        if should_fail:
            raise RuntimeError("Transient system error")
        return "success_recovered"

    wf = WorkflowDefinition(
        name="flaky_flow",
        stages=(
            StageDefinition(
                name="stage_flaky",
                steps=(
                    StepDefinition(name="step_ok", action=lambda ctx: "ok"),
                    StepDefinition(
                        name="step_fail", action=_flaky_step, depends_on=("step_ok",)
                    ),
                ),
            ),
        ),
    )

    result = runner.execute(wf)
    status = result.status
    failed = result.failed_steps

    assert status == "SUSPENDED"
    assert "step_fail" in failed

    # Verify suspended event published
    events = [call[0][0] for call in mock_event_bus.publish.call_args_list]
    suspended_events = [e for e in events if isinstance(e, WorkflowSuspendedEvent)]
    assert len(suspended_events) == 1

    # Now recover and resume
    should_fail = False
    resumed_result = runner.resume(result.run_id, wf)
    resumed_status = resumed_result.status
    resumed_completed = resumed_result.completed_steps

    assert resumed_status == "COMPLETED"
    assert "step_ok" in resumed_completed
    assert "step_fail" in resumed_completed


def test_runner_abort() -> None:
    """Validate aborting a workflow with rollback compensation."""
    mock_event_bus = MagicMock(spec=EventBusPort)
    runner = CqrsWorkflowRunner(event_bus=mock_event_bus)

    compensated = False

    def _comp(ctx) -> None:
        nonlocal compensated
        compensated = True

    wf = WorkflowDefinition(
        name="abort_flow",
        stages=(
            StageDefinition(
                name="stage_1",
                steps=(
                    StepDefinition(
                        name="step_1",
                        action=lambda ctx: "done",
                        compensation=_comp,
                    ),
                    StepDefinition(
                        name="step_2",
                        action=lambda ctx: (_ for _ in ()).throw(ValueError("Boom")),
                        depends_on=("step_1",),
                    ),
                ),
            ),
        ),
    )

    result = runner.execute(wf)
    assert result.status == "SUSPENDED"

    abort_res = runner.abort(result.run_id, wf, reason="Operator cancelled bad run")
    abort_status = abort_res.status
    assert abort_status == "CANCELLED"
    assert compensated is True

    # Verify aborted event
    events = [call[0][0] for call in mock_event_bus.publish.call_args_list]
    aborted_events = [e for e in events if isinstance(e, WorkflowAbortedEvent)]
    assert len(aborted_events) == 1
    assert aborted_events[0].reason == "Operator cancelled bad run"


def test_runner_worker_pools_and_context_managers() -> None:
    """Validate runner configuration with worker pools and context managers."""
    with CqrsWorkflowRunner(max_process_workers=2, max_thread_workers=4) as runner:
        engine = runner._engine
        assert hasattr(engine, "_max_process_workers")
        p_workers = getattr(engine, "_max_process_workers", None)
        assert p_workers == 2
        t_workers = getattr(engine, "_max_thread_workers", None)
        assert t_workers == 4


async def test_runner_async_context_manager() -> None:
    """Validate runner async context manager cleanly releases engine pools."""
    async with CqrsWorkflowRunner(max_process_workers=1) as runner:
        engine = runner._engine
        assert engine is not None


def test_runner_rewind() -> None:
    """Validate rewinding a workflow to a historical step and replaying."""
    runner = CqrsWorkflowRunner()
    counter = 0

    def _inc(ctx) -> int:
        nonlocal counter
        counter += 1
        return counter

    wf = WorkflowDefinition(
        name="rewind_flow",
        stages=(
            StageDefinition(
                name="stage_1",
                steps=(
                    StepDefinition(name="step_1", action=lambda ctx: "first"),
                    StepDefinition(
                        name="step_2",
                        action=_inc,
                        depends_on=("step_1",),
                    ),
                ),
            ),
        ),
    )

    initial_res = runner.execute(wf)
    status_init = initial_res.status
    assert status_init == "COMPLETED"
    assert counter == 1

    rewound_res = runner.rewind(initial_res.run_id, wf, to_step="step_2")
    status_rewound = rewound_res.status
    assert status_rewound == "COMPLETED"
    assert counter == 2


def test_runner_simulate() -> None:
    """Validate dry-run simulation through CqrsWorkflowRunner."""
    runner = CqrsWorkflowRunner()
    called = False

    def _action(ctx) -> str:
        nonlocal called
        called = True
        return "actual"

    wf = WorkflowDefinition(
        name="sim_flow",
        stages=(
            StageDefinition(
                name="stage_1",
                steps=(
                    StepDefinition(
                        name="step_1",
                        action=_action,
                        dry_run=lambda ctx: "mocked",
                    ),
                ),
            ),
        ),
    )

    sim_res = runner.simulate(wf)
    sim_status = sim_res.status
    assert sim_status == "COMPLETED"
    assert called is False
    assert sim_res.outputs["step_1"] == "mocked"


def test_runner_render() -> None:
    """Validate diagram rendering through CqrsWorkflowRunner."""
    runner = CqrsWorkflowRunner()
    wf = WorkflowDefinition(
        name="render_flow",
        stages=(
            StageDefinition(
                name="stage_1",
                steps=(
                    StepDefinition(name="step_a", action=lambda ctx: 1),
                    StepDefinition(
                        name="step_b", action=lambda ctx: 2, depends_on=("step_a",)
                    ),
                ),
            ),
        ),
    )

    mermaid_out = runner.render(wf, format_name="mermaid")
    assert "graph" in mermaid_out or "flowchart" in mermaid_out
    assert "step_a" in mermaid_out
    assert "step_b" in mermaid_out


def test_runner_middleware() -> None:
    """Validate middleware pipeline registration and invocation in CqrsWorkflowRunner."""
    from hexaflow.adapters.middleware import InOutStepMiddleware

    intercepted = []

    class AuditMiddleware(InOutStepMiddleware):
        def before(self, ctx):
            intercepted.append(f"before:{ctx.step_name}")
            return ctx.step_name

        def after(self, ctx, result, context):
            intercepted.append(f"after:{context}")
            return result

    audit_mw = AuditMiddleware()
    runner = CqrsWorkflowRunner(middleware=[audit_mw])

    wf = WorkflowDefinition(
        name="mw_flow",
        stages=(
            StageDefinition(
                name="stage_1",
                steps=(StepDefinition(name="step_x", action=lambda ctx: "x"),),
            ),
        ),
    )

    res = runner.execute(wf)
    res_status = res.status
    assert res_status == "COMPLETED"
    assert intercepted == ["before:step_x", "after:step_x"]

    # Test runner.use() chaining
    runner_chained = CqrsWorkflowRunner()
    res_use = runner_chained.use(audit_mw)
    assert res_use is runner_chained

    # Test custom engine passed in with middleware
    from hexaflow.adapters.engines.local_async import AsyncioWorkflowEngine

    custom_engine = AsyncioWorkflowEngine()
    runner_custom = CqrsWorkflowRunner(engine=custom_engine, middleware=[audit_mw])
    assert runner_custom is not None
    assert len(custom_engine._middleware) >= 1
