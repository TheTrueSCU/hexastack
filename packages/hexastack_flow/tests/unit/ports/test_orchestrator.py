"""Unit tests for CqrsWorkflowOrchestratorPort abstract contract.

Notes/Architectural Intent:
    Ensures CqrsWorkflowOrchestratorPort enforces abstract method implementation
    on subclasses.
"""

from typing import Any

import pytest
from hexaflow.domain.models import WorkflowDefinition

from hexastack_flow.domain.models import WorkflowExecutionResult
from hexastack_flow.ports.orchestrator import CqrsWorkflowOrchestratorPort


def test_orchestrator_port_cannot_be_instantiated_directly() -> None:
    """Ensure CqrsWorkflowOrchestratorPort is abstract."""
    port_cls: type[CqrsWorkflowOrchestratorPort] = CqrsWorkflowOrchestratorPort
    with pytest.raises(TypeError):
        port_cls.__new__(port_cls)


def test_concrete_orchestrator_subclass() -> None:
    """Verify concrete subclass can implement all abstract methods."""

    class DummyOrchestrator(CqrsWorkflowOrchestratorPort):
        def execute(
            self,
            workflow: WorkflowDefinition,
            initial_inputs: dict[str, Any] | None = None,
        ) -> WorkflowExecutionResult:
            from datetime import UTC, datetime

            return WorkflowExecutionResult(
                run_id="run-1",
                workflow_name=workflow.name,
                status="COMPLETED",
                completed_steps=(),
                failed_steps=(),
                outputs={},
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
            )

        def resume(
            self,
            run_id: str,
            workflow: WorkflowDefinition,
            patch_inputs: dict[str, Any] | None = None,
        ) -> WorkflowExecutionResult:
            from datetime import UTC, datetime

            return WorkflowExecutionResult(
                run_id=run_id,
                workflow_name=workflow.name,
                status="COMPLETED",
                completed_steps=(),
                failed_steps=(),
                outputs={},
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
            )

        def abort(
            self,
            run_id: str,
            workflow: WorkflowDefinition,
            reason: str = "Operator aborted",
        ) -> WorkflowExecutionResult:
            from datetime import UTC, datetime

            return WorkflowExecutionResult(
                run_id=run_id,
                workflow_name=workflow.name,
                status="CANCELLED",
                completed_steps=(),
                failed_steps=(),
                outputs={},
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
            )

        def rewind(
            self,
            run_id: str,
            workflow: WorkflowDefinition,
            to_step: str,
            patch_inputs: dict[str, Any] | None = None,
            skip_steps: set[str] | list[str] | None = None,
        ) -> WorkflowExecutionResult:
            return self.execute(workflow)

        def simulate(
            self,
            workflow: WorkflowDefinition,
            initial_inputs: dict[str, Any] | None = None,
            allow_unsafe: bool = False,
            fault_injection: dict[str, Exception] | None = None,
        ) -> WorkflowExecutionResult:
            return self.execute(workflow)

        def render(
            self,
            workflow: WorkflowDefinition,
            format_name: str = "mermaid",
            options: Any | None = None,
        ) -> str:
            return "graph LR\n    A --> B"

        def close(self) -> None:
            pass

    orch = DummyOrchestrator()
    wf = WorkflowDefinition(name="test_wf", stages=())
    res = orch.execute(wf)
    status = res.status
    assert status == "COMPLETED"

    res_resume = orch.resume("run-1", wf)
    status_resume = res_resume.status
    assert status_resume == "COMPLETED"

    res_abort = orch.abort("run-1", wf)
    status_abort = res_abort.status
    assert status_abort == "CANCELLED"

    res_rewind = orch.rewind("run-1", wf, to_step="step_1")
    status_rewind = res_rewind.status
    assert status_rewind == "COMPLETED"

    res_sim = orch.simulate(wf)
    status_sim = res_sim.status
    assert status_sim == "COMPLETED"

    diagram = orch.render(wf, format_name="mermaid", options=None)
    assert "graph LR" in diagram

    orch.close()


async def test_orchestrator_aclose() -> None:
    """Verify asynchronous aclose delegates cleanly."""
    from datetime import UTC, datetime

    class AsyncOrchestrator(CqrsWorkflowOrchestratorPort):
        def execute(self, workflow, initial_inputs=None):
            return WorkflowExecutionResult(
                run_id="r1",
                workflow_name=workflow.name,
                status="COMPLETED",
                completed_steps=(),
                failed_steps=(),
                outputs={},
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
            )

        def resume(self, run_id, workflow, patch_inputs=None):
            return self.execute(workflow)

        def abort(self, run_id, workflow, reason="Operator aborted"):
            return self.execute(workflow)

        def rewind(self, run_id, workflow, to_step, patch_inputs=None, skip_steps=None):
            return self.execute(workflow)

        def simulate(
            self,
            workflow,
            initial_inputs=None,
            allow_unsafe=False,
            fault_injection=None,
        ):
            return self.execute(workflow)

        def render(self, workflow, format_name="mermaid", options=None):
            return "graph TD"

        def close(self) -> None:
            self.closed = True

    orch = AsyncOrchestrator()
    await orch.aclose()
    closed = getattr(orch, "closed", False)
    assert closed is True
