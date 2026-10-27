"""Hexaqueue distributed workflow orchestrator adapter implementing CqrsWorkflowOrchestratorPort.

Notes/Architectural Intent:
    Translates hexaflow WorkflowDefinition DAGs into Hexaqueue pipeline RunSpecs,
    dispatches executions to a remote Hexaqueue cluster via REST endpoints, streams
    real-time progress via Server-Sent Events (SSE) or polling, and translates
    remote execution checkpoints into Hexastack WorkflowExecutionResult objects
    and domain events.
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

from hexaflow.domain.exceptions import WorkflowError
from hexaflow.domain.models import WorkflowDefinition

from hexastack_core.utils.imports import require_dependency
from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_flow.domain.events import (
    WorkflowAbortedEvent,
    WorkflowCompletedEvent,
    WorkflowStartedEvent,
    WorkflowStepCompletedEvent,
    WorkflowSuspendedEvent,
)
from hexastack_flow.domain.models import WorkflowExecutionResult
from hexastack_flow.ports.orchestrator import CqrsWorkflowOrchestratorPort

__all__ = [
    "HexaqueueWorkflowOrchestratorAdapter",
]


class HexaqueueWorkflowOrchestratorAdapter(CqrsWorkflowOrchestratorPort):
    """Distributed workflow orchestrator offloading DAG execution to Hexaqueue.

    Notes/Architectural Intent:
        Implements CqrsWorkflowOrchestratorPort to offload large or distributed
        workflows across a remote Hexaqueue worker cluster while preserving
        local CQRS event publication and execution semantics.
    """

    def __init__(
        self,
        cluster_url: str = "http://localhost:8000",
        token: str | None = None,
        event_bus: EventBusPort | None = None,
        client: Any | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Initialize Hexaqueue orchestrator adapter.

        Args:
            cluster_url: Base URL of the Hexaqueue cluster coordinator.
            token: Optional Bearer authentication token.
            event_bus: Optional EventBusPort to publish workflow lifecycle events.
            client: Optional pre-configured httpx.Client instance for testing.
            timeout_seconds: HTTP client timeout in seconds.
        """
        httpx = require_dependency(
            "httpx",
            extra="hexaqueue",
            package="hexastack-flow",
            feature_name="HexaqueueWorkflowOrchestratorAdapter",
        )

        self._cluster_url = cluster_url.rstrip("/")
        self._event_bus = event_bus

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "hexastack-flow-hexaqueue-orchestrator",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._client = client or httpx.Client(
            base_url=self._cluster_url,
            headers=headers,
            timeout=timeout_seconds,
        )

    def _to_definition(self, workflow: Any) -> WorkflowDefinition:
        """Resolve a Workflow DSL instance or WorkflowDefinition to WorkflowDefinition."""
        if hasattr(workflow, "to_definition") and callable(workflow.to_definition):
            return workflow.to_definition()
        return workflow

    def compile_workflow(
        self,
        workflow: WorkflowDefinition | Any,
        initial_inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compile a WorkflowDefinition DAG into a Hexaqueue pipeline specification.

        Args:
            workflow: WorkflowDefinition or Workflow DSL instance.
            initial_inputs: Optional dictionary of root arguments.

        Returns:
            Dictionary representation of Hexaqueue RunSpec containing jobs and dependencies.
        """
        wf_def = self._to_definition(workflow)
        jobs: list[dict[str, Any]] = []
        dependencies: list[dict[str, str]] = []

        for stage in wf_def.stages:
            for step in stage.steps:
                job_spec: dict[str, Any] = {
                    "id": step.name,
                    "name": step.name,
                    "stage": stage.name,
                    "timeout_seconds": step.timeout_seconds,
                    "max_attempts": (
                        step.retry_policy.max_attempts if step.retry_policy else 1
                    ),
                    "payload": initial_inputs or {},
                    "metadata": dict(step.metadata) if step.metadata else {},
                }
                jobs.append(job_spec)
                for dep in step.depends_on:
                    dependencies.append({"parent": dep, "child": step.name})

        return {
            "workflow_name": wf_def.name,
            "version": wf_def.version,
            "description": wf_def.description,
            "jobs": jobs,
            "dependencies": dependencies,
            "initial_inputs": initial_inputs or {},
        }

    def execute(
        self,
        workflow: WorkflowDefinition | Any,
        initial_inputs: dict[str, Any] | None = None,
    ) -> WorkflowExecutionResult:
        """Execute a workflow definition remotely on Hexaqueue cluster.

        Args:
            workflow: The workflow DAG definition to execute.
            initial_inputs: Optional dictionary of root arguments.

        Returns:
            WorkflowExecutionResult containing terminal execution outcome.

        Raises:
            WorkflowError: If workflow submission or remote execution encounters fatal error.
        """
        wf_def = self._to_definition(workflow)
        spec = self.compile_workflow(wf_def, initial_inputs)

        resp = self._client.post("/api/v1/runs", json=spec)
        if resp.status_code not in (200, 201):
            raise WorkflowError(
                f"Failed to submit workflow run to Hexaqueue: {resp.text}"
            )

        data = resp.json()
        run_id = str(data.get("id", ""))
        started_at = datetime.now(UTC)

        if self._event_bus is not None:
            self._event_bus.publish(
                WorkflowStartedEvent(
                    run_id=run_id,
                    workflow_name=wf_def.name,
                    started_at=started_at,
                )
            )

        terminal_state = self._stream_or_poll_run(run_id, wf_def.name)
        result = self._to_result(terminal_state, wf_def.name, started_at)
        self._emit_terminal_events(result)
        return result

    def resume(
        self,
        run_id: str,
        workflow: WorkflowDefinition | Any,
        patch_inputs: dict[str, Any] | None = None,
    ) -> WorkflowExecutionResult:
        """Resume a suspended workflow run on the remote Hexaqueue cluster.

        Args:
            run_id: The unique identifier of the suspended workflow run.
            workflow: WorkflowDefinition matching the run.
            patch_inputs: Optional dictionary of replacement inputs for the resumed step.

        Returns:
            WorkflowExecutionResult reflecting post-resumption status.

        Raises:
            WorkflowError: If the run cannot be resumed or does not exist.
        """
        wf_def = self._to_definition(workflow)
        body = {"patch_inputs": patch_inputs or {}}
        resp = self._client.post(f"/api/v1/runs/{run_id}/resume", json=body)
        if resp.status_code == 404:
            raise WorkflowError(f"Workflow run '{run_id}' not found.")
        if resp.status_code not in (200, 202):
            raise WorkflowError(f"Failed to resume workflow run: {resp.text}")

        started_at = datetime.now(UTC)
        terminal_state = self._stream_or_poll_run(run_id, wf_def.name)
        result = self._to_result(terminal_state, wf_def.name, started_at)
        self._emit_terminal_events(result)
        return result

    def abort(
        self,
        run_id: str,
        workflow: WorkflowDefinition | Any,
        reason: str = "Operator aborted",
    ) -> WorkflowExecutionResult:
        """Abort a workflow and cancel execution on Hexaqueue cluster.

        Args:
            run_id: The unique identifier of the workflow run to cancel.
            workflow: WorkflowDefinition containing compensation hooks.
            reason: Operator rationale or explanation for cancellation.

        Returns:
            WorkflowExecutionResult reflecting the aborted state.

        Raises:
            WorkflowError: If abort operation fails or run does not exist.
        """
        wf_def = self._to_definition(workflow)
        body = {"reason": reason}
        resp = self._client.post(f"/api/v1/runs/{run_id}/cancel", json=body)
        if resp.status_code == 404:
            raise WorkflowError(f"Workflow run '{run_id}' not found.")
        if resp.status_code not in (200, 202):
            raise WorkflowError(f"Failed to abort workflow run: {resp.text}")

        data = resp.json() if resp.text else {}
        aborted_at = datetime.now(UTC)

        result = self._to_result(data, wf_def.name, aborted_at)
        if self._event_bus is not None:
            self._event_bus.publish(
                WorkflowAbortedEvent(
                    run_id=run_id,
                    workflow_name=wf_def.name,
                    reason=reason,
                    aborted_at=aborted_at,
                )
            )
        return result

    def rewind(
        self,
        run_id: str,
        workflow: WorkflowDefinition | Any,
        to_step: str,
        patch_inputs: dict[str, Any] | None = None,
        skip_steps: set[str] | Sequence[str] | None = None,
    ) -> WorkflowExecutionResult:
        """Rewind workflow execution on Hexaqueue to before a specified step.

        Args:
            run_id: The unique identifier of the workflow run to rewind.
            workflow: WorkflowDefinition matching the run.
            to_step: The target step identifier to rewind before.
            patch_inputs: Optional override inputs for the resumed step frontier.
            skip_steps: Optional collection of step names to explicitly skip.

        Returns:
            WorkflowExecutionResult reflecting replay status.

        Raises:
            WorkflowError: If to_step is invalid or rewind fails.
        """
        wf_def = self._to_definition(workflow)
        body = {
            "to_step": to_step,
            "patch_inputs": patch_inputs or {},
            "skip_steps": list(skip_steps or []),
        }
        resp = self._client.post(f"/api/v1/runs/{run_id}/rewind", json=body)
        if resp.status_code == 404:
            raise WorkflowError(f"Workflow run '{run_id}' not found.")
        if resp.status_code not in (200, 202):
            raise WorkflowError(f"Failed to rewind workflow run: {resp.text}")

        started_at = datetime.now(UTC)
        terminal_state = self._stream_or_poll_run(run_id, wf_def.name)
        result = self._to_result(terminal_state, wf_def.name, started_at)
        self._emit_terminal_events(result)
        return result

    def simulate(
        self,
        workflow: WorkflowDefinition | Any,
        initial_inputs: dict[str, Any] | None = None,
        allow_unsafe: bool = False,
        fault_injection: dict[str, Exception] | None = None,
    ) -> WorkflowExecutionResult:
        """Perform a dry-run simulation of the workflow DAG without side effects.

        Args:
            workflow: The workflow DAG definition to simulate.
            initial_inputs: Optional dictionary of root arguments.
            allow_unsafe: When True, executes side-effecting steps without mocks.
            fault_injection: Optional mapping of step names to simulated Exceptions.

        Returns:
            WorkflowExecutionResult summarizing the simulated outcome.

        Raises:
            WorkflowError: If simulation validation or submission encounters fatal error.
        """
        wf_def = self._to_definition(workflow)
        spec = self.compile_workflow(wf_def, initial_inputs)
        fault_names = {k: type(v).__name__ for k, v in (fault_injection or {}).items()}
        spec["dry_run"] = True
        spec["allow_unsafe"] = allow_unsafe
        spec["fault_injection"] = fault_names

        resp = self._client.post("/api/v1/runs/simulate", json=spec)
        if resp.status_code not in (200, 201):
            raise WorkflowError(f"Simulation failed on Hexaqueue cluster: {resp.text}")

        data = resp.json()
        now = datetime.now(UTC)
        return self._to_result(data, wf_def.name, now)

    def render(
        self,
        workflow: WorkflowDefinition | Any,
        format_name: str = "mermaid",
        options: Any | None = None,
    ) -> str:
        """Render the workflow DAG into a visual diagram or structural format.

        Args:
            workflow: The workflow DAG definition to visualize.
            format_name: Name of renderer format ('mermaid', 'dot', 'ascii', 'json').
            options: Optional renderer options (direction, critical path, highlight nodes).

        Returns:
            Rendered diagram or structured output string.
        """
        from hexaflow.adapters.renderers import default_renderer_registry
        from hexaflow.domain.graph import WorkflowGraph

        wf_def = self._to_definition(workflow)
        graph = WorkflowGraph.from_workflow(wf_def)
        renderer = default_renderer_registry.get(format_name)
        if options is not None:
            return renderer.render(graph, options=options)
        return renderer.render(graph)

    def _stream_or_poll_run(self, run_id: str, workflow_name: str) -> dict[str, Any]:
        """Stream progress via Server-Sent Events or fallback to polling."""
        # Try SSE stream first
        try:
            with self._client.stream(
                "GET", f"/api/v1/runs/{run_id}/stream"
            ) as stream_resp:
                if stream_resp.status_code == 200:
                    terminal_data = self._consume_sse_stream(
                        run_id, workflow_name, stream_resp
                    )
                    if terminal_data:
                        return terminal_data
        except Exception:
            pass

        return self._poll_run_state(run_id)

    def _consume_sse_stream(
        self,
        run_id: str,
        workflow_name: str,
        stream_resp: Any,
    ) -> dict[str, Any] | None:
        """Consume SSE event stream, emitting step events until terminal state."""
        emitted_steps: set[str] = set()
        terminal_statuses = {"COMPLETED", "FAILED", "SUSPENDED", "ABORTED", "CANCELLED"}

        for line in stream_resp.iter_lines():
            line_str = line.strip()
            if not line_str or not line_str.startswith("data:"):
                continue

            payload_raw = line_str.removeprefix("data:").strip()
            try:
                event_dict = json.loads(payload_raw)
            except json.JSONDecodeError:
                continue

            event_type = str(event_dict.get("type", ""))
            if event_type == "step_completed":
                step_name = str(event_dict.get("step_name", ""))
                if step_name and step_name not in emitted_steps:
                    emitted_steps.add(step_name)
                    if self._event_bus is not None:
                        self._event_bus.publish(
                            WorkflowStepCompletedEvent(
                                run_id=run_id,
                                stage_name=str(event_dict.get("stage_name", "")),
                                step_name=step_name,
                                attempt_number=int(event_dict.get("attempt_number", 1)),
                                duration_seconds=float(
                                    event_dict.get("duration_seconds", 0.0)
                                ),
                                output_summary=dict(event_dict.get("output", {})),
                            )
                        )

            status = str(event_dict.get("status", "")).upper()
            if status in terminal_statuses:
                return event_dict

        return None

    def _poll_run_state(self, run_id: str) -> dict[str, Any]:
        """Poll status endpoint for terminal run outcome."""
        resp = self._client.get(f"/api/v1/runs/{run_id}")
        if resp.status_code == 404:
            raise WorkflowError(f"Workflow run '{run_id}' not found.")
        resp.raise_for_status()
        return resp.json()

    def _to_result(
        self,
        data: dict[str, Any],
        workflow_name: str,
        started_at: datetime,
    ) -> WorkflowExecutionResult:
        """Map raw cluster response dictionary into WorkflowExecutionResult."""
        run_id = str(data.get("id") or data.get("run_id") or "unknown-run")
        status = str(data.get("status", "COMPLETED")).upper()
        if status == "CANCELLED":
            status = "ABORTED"

        completed = tuple(str(s) for s in data.get("completed_steps", []))
        failed = tuple(str(s) for s in data.get("failed_steps", []))
        outputs = dict(data.get("outputs", {}))
        error_summary = data.get("error_summary") or data.get("error")

        return WorkflowExecutionResult(
            run_id=run_id,
            workflow_name=str(data.get("workflow_name") or workflow_name),
            status=status,
            completed_steps=completed,
            failed_steps=failed,
            outputs=outputs,
            started_at=started_at,
            ended_at=datetime.now(UTC),
            error_summary=str(error_summary) if error_summary else None,
        )

    def _emit_terminal_events(self, result: WorkflowExecutionResult) -> None:
        """Emit terminal CQRS domain events based on workflow execution result."""
        if self._event_bus is None:
            return

        if result.status == "COMPLETED":
            self._event_bus.publish(
                WorkflowCompletedEvent(
                    run_id=result.run_id,
                    workflow_name=result.workflow_name,
                    completed_at=result.ended_at,
                    total_steps=len(result.completed_steps),
                )
            )
        elif result.status in ("SUSPENDED", "FAILED"):
            failed_step = result.failed_steps[0] if result.failed_steps else "unknown"
            self._event_bus.publish(
                WorkflowSuspendedEvent(
                    run_id=result.run_id,
                    stage_name="default",
                    step_name=failed_step,
                    error_type="StepExecutionError",
                    error_message=result.error_summary
                    or "Remote step execution failed.",
                )
            )

    def close(self) -> None:
        """Release underlying HTTP client resources."""
        if hasattr(self._client, "close") and callable(self._client.close):
            self._client.close()

    async def aclose(self) -> None:
        """Asynchronously release underlying HTTP client resources."""
        self.close()

    def __enter__(self) -> "HexaqueueWorkflowOrchestratorAdapter":
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, releasing HTTP resources."""
        self.close()

    async def __aenter__(self) -> "HexaqueueWorkflowOrchestratorAdapter":
        """Enter async context manager."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager, releasing HTTP resources."""
        await self.aclose()
