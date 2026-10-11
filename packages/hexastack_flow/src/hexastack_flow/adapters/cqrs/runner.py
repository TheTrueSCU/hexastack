"""CQRS workflow runner adapter implementing CqrsWorkflowOrchestratorPort.

Notes/Architectural Intent:
    Glues the hexaflow execution engine, state store, and event bus together.
    Translates hexaflow state objects into Hexastack domain results and
    publishes lifecycle domain events.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

from hexaflow.adapters.engines.local_async import AsyncioWorkflowEngine
from hexaflow.adapters.storage.in_memory import InMemoryStateStore
from hexaflow.domain.models import WorkflowDefinition
from hexaflow.domain.state import StepStatus, WorkflowExecutionState, WorkflowStatus
from hexaflow.ports.engine import WorkflowEnginePort
from hexaflow.ports.middleware import StepMiddlewarePort
from hexaflow.ports.storage import WorkflowStateStorePort

from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_flow.domain.events import (
    WorkflowAbortedEvent,
    WorkflowCompletedEvent,
    WorkflowStartedEvent,
    WorkflowSuspendedEvent,
)
from hexastack_flow.domain.models import WorkflowExecutionResult
from hexastack_flow.ports.orchestrator import CqrsWorkflowOrchestratorPort

__all__ = [
    "CqrsWorkflowRunner",
]


class CqrsWorkflowRunner(CqrsWorkflowOrchestratorPort):
    """Orchestrator runner coordinating workflow execution with CQRS buses.

    Notes/Architectural Intent:
        Implements CqrsWorkflowOrchestratorPort to provide a complete
        in-process execution runtime with automatic event publishing.
    """

    def __init__(
        self,
        state_store: WorkflowStateStorePort | None = None,
        engine: WorkflowEnginePort | None = None,
        event_bus: EventBusPort | None = None,
        max_process_workers: int | None = None,
        max_thread_workers: int | None = None,
        middleware: Sequence[StepMiddlewarePort] | None = None,
    ) -> None:
        """Initialize runner with state store, execution engine, and event bus.

        Args:
            state_store: WorkflowStateStorePort for persistence. Defaults to InMemoryStateStore.
            engine: WorkflowEnginePort for DAG execution. Defaults to AsyncioWorkflowEngine.
            event_bus: Optional EventBusPort for publishing workflow domain events.
            max_process_workers: Optional maximum worker processes for ExecutionPool.PROCESS.
            max_thread_workers: Optional maximum worker threads for ExecutionPool.THREAD.
            middleware: Optional sequence of StepMiddlewarePort interceptors.
        """
        self._store = state_store or InMemoryStateStore()
        self._engine = engine or AsyncioWorkflowEngine(
            state_store=self._store,
            max_process_workers=max_process_workers,
            max_thread_workers=max_thread_workers,
            middleware=middleware,
        )
        if engine is not None and middleware:
            use_fn = getattr(self._engine, "use", None)
            if callable(use_fn):
                for mw in middleware:
                    use_fn(mw)
        self._event_bus = event_bus

    def use(self, middleware: StepMiddlewarePort) -> "CqrsWorkflowRunner":
        """Register a StepMiddlewarePort interceptor onto the underlying engine.

        Args:
            middleware: StepMiddlewarePort interceptor instance.

        Returns:
            Self for fluent chaining.
        """
        use_fn = getattr(self._engine, "use", None)
        if callable(use_fn):
            use_fn(middleware)
        return self

    def execute(
        self,
        workflow: WorkflowDefinition,
        initial_inputs: dict[str, Any] | None = None,
    ) -> WorkflowExecutionResult:
        """Execute workflow definition from the first stage.

        Args:
            workflow: The WorkflowDefinition to run.
            initial_inputs: Optional dictionary of root arguments.

        Returns:
            WorkflowExecutionResult summarizing status, step outputs, and timing.
        """
        start_time = datetime.now(UTC)
        state = self._engine.run(workflow, initial_inputs=initial_inputs)

        if self._event_bus is not None:
            self._event_bus.publish(
                WorkflowStartedEvent(
                    run_id=state.run_id,
                    workflow_name=state.workflow_name,
                    started_at=start_time,
                )
            )

        self._emit_terminal_events(state)
        return self._to_result(state)

    def resume(
        self,
        run_id: str,
        workflow: WorkflowDefinition,
        patch_inputs: dict[str, Any] | None = None,
    ) -> WorkflowExecutionResult:
        """Resume a suspended workflow run from its latest checkpoints.

        Args:
            run_id: Unique identifier of the suspended run.
            workflow: WorkflowDefinition specification matching the run.
            patch_inputs: Optional updated inputs for the suspended step.

        Returns:
            WorkflowExecutionResult reflecting post-resumption status.
        """
        state = self._engine.resume(run_id, workflow, patch_inputs=patch_inputs)
        self._emit_terminal_events(state)
        return self._to_result(state)

    def abort(
        self,
        run_id: str,
        workflow: WorkflowDefinition,
        reason: str = "Operator aborted",
    ) -> WorkflowExecutionResult:
        """Abort a workflow and unwind completed steps via compensation hooks.

        Args:
            run_id: Unique identifier of the workflow run.
            workflow: WorkflowDefinition specification containing compensation hooks.
            reason: Operator rationale or explanation for cancellation.

        Returns:
            WorkflowExecutionResult reflecting the aborted state.
        """
        state = self._engine.abort(run_id, workflow)

        if self._event_bus is not None:
            self._event_bus.publish(
                WorkflowAbortedEvent(
                    run_id=state.run_id,
                    workflow_name=state.workflow_name,
                    reason=reason,
                    aborted_at=datetime.now(UTC),
                )
            )

        return self._to_result(state)

    def rewind(
        self,
        run_id: str,
        workflow: WorkflowDefinition,
        to_step: str,
        patch_inputs: dict[str, Any] | None = None,
        skip_steps: set[str] | list[str] | None = None,
    ) -> WorkflowExecutionResult:
        """Rewind workflow execution to before a step and re-evaluate downstream steps.

        Args:
            run_id: Unique identifier of the workflow run to rewind.
            workflow: WorkflowDefinition matching the run.
            to_step: The target step identifier to rewind before.
            patch_inputs: Optional override inputs for the resumed step frontier.
            skip_steps: Optional collection of step names to explicitly skip.

        Returns:
            WorkflowExecutionResult reflecting post-rewind replay outcome.
        """
        state = self._engine.rewind(
            run_id=run_id,
            workflow=workflow,
            to_step=to_step,
            patch_inputs=patch_inputs,
            skip_steps=skip_steps,
        )
        self._emit_terminal_events(state)
        return self._to_result(state)

    def simulate(
        self,
        workflow: WorkflowDefinition,
        initial_inputs: dict[str, Any] | None = None,
        allow_unsafe: bool = False,
        fault_injection: dict[str, Exception] | None = None,
    ) -> WorkflowExecutionResult:
        """Perform a dry-run simulation of the workflow DAG without mutating production systems.

        Args:
            workflow: The WorkflowDefinition to simulate.
            initial_inputs: Optional dictionary of root arguments.
            allow_unsafe: When True, executes side-effecting steps without mocks.
            fault_injection: Optional mapping of step names to simulated Exceptions.

        Returns:
            WorkflowExecutionResult reflecting the simulated execution state.
        """
        state = self._engine.run(
            workflow=workflow,
            initial_inputs=initial_inputs,
            dry_run=True,
            allow_unsafe=allow_unsafe,
            fault_injection=fault_injection,
        )
        return self._to_result(state)

    def render(
        self,
        workflow: WorkflowDefinition,
        format_name: str = "mermaid",
    ) -> str:
        """Render the workflow DAG into a visual diagram or structural format.

        Args:
            workflow: The WorkflowDefinition to visualize.
            format_name: Name of renderer format ('mermaid', 'dot', 'ascii', 'json').

        Returns:
            Rendered diagram or structured output string.
        """
        from hexaflow.adapters.renderers import default_renderer_registry
        from hexaflow.domain.graph import WorkflowGraph

        graph = WorkflowGraph.from_workflow(workflow)
        renderer = default_renderer_registry.get(format_name)
        return renderer.render(graph)

    def close(self) -> None:
        """Release underlying engine worker pools and execution resources."""
        self._engine.close()

    async def aclose(self) -> None:
        """Asynchronously release underlying engine worker pools and resources."""
        await self._engine.aclose()

    def __enter__(self) -> "CqrsWorkflowRunner":
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, releasing engine worker pools."""
        self.close()

    async def __aenter__(self) -> "CqrsWorkflowRunner":
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager, asynchronously releasing engine worker pools."""
        await self.aclose()

    def _emit_terminal_events(self, state: WorkflowExecutionState) -> None:
        """Publish lifecycle events based on execution state outcome.

        Args:
            state: WorkflowExecutionState to inspect.
        """
        if self._event_bus is None:
            return

        if state.status == WorkflowStatus.COMPLETED:
            self._event_bus.publish(
                WorkflowCompletedEvent(
                    run_id=state.run_id,
                    workflow_name=state.workflow_name,
                    completed_at=state.finished_at or datetime.now(UTC),
                    total_steps=len(state.step_checkpoints),
                )
            )
        elif state.status == WorkflowStatus.SUSPENDED:
            failed_step = next(
                (
                    name
                    for name, chk in state.step_checkpoints.items()
                    if chk.status == StepStatus.FAILED
                ),
                "unknown",
            )
            self._event_bus.publish(
                WorkflowSuspendedEvent(
                    run_id=state.run_id,
                    stage_name=state.current_stage or "unknown",
                    step_name=failed_step,
                    error_type="StepExecutionError",
                    error_message=state.error_summary
                    or "Step failed and exhausted retries.",
                )
            )

    @staticmethod
    def _to_result(state: WorkflowExecutionState) -> WorkflowExecutionResult:
        """Map a hexaflow WorkflowExecutionState into a WorkflowExecutionResult.

        Args:
            state: Engine execution state.

        Returns:
            Pydantic WorkflowExecutionResult value object.
        """
        completed = tuple(
            name
            for name, chk in state.step_checkpoints.items()
            if chk.status == StepStatus.COMPLETED
        )
        failed = tuple(
            name
            for name, chk in state.step_checkpoints.items()
            if chk.status == StepStatus.FAILED
        )
        outputs = {
            name: chk.output_payload
            for name, chk in state.step_checkpoints.items()
            if chk.output_payload is not None
        }

        return WorkflowExecutionResult(
            run_id=state.run_id,
            workflow_name=state.workflow_name,
            status=state.status.value,
            completed_steps=completed,
            failed_steps=failed,
            outputs=outputs,
            started_at=state.started_at,
            ended_at=state.finished_at or datetime.now(UTC),
            error_summary=state.error_summary,
        )
