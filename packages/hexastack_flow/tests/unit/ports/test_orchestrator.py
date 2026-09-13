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
    with pytest.raises(TypeError):
        CqrsWorkflowOrchestratorPort()  # type: ignore[abstract]


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

    orch = DummyOrchestrator()
    wf = WorkflowDefinition(name="test_wf", stages=())
    res = orch.execute(wf)
    assert res.status == "COMPLETED"

    res_resume = orch.resume("run-1", wf)
    assert res_resume.status == "COMPLETED"

    res_abort = orch.abort("run-1", wf)
    assert res_abort.status == "CANCELLED"
