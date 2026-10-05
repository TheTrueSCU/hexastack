"""Unit tests for hexastack_flow domain models.

Notes/Architectural Intent:
    Validates immutability, field constraints, and serialization of
    CqrsStepMetadata and WorkflowExecutionResult domain models.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from hexastack_flow.domain.models import CqrsStepMetadata, WorkflowExecutionResult


def test_cqrs_step_metadata_creation() -> None:
    """Validate construction and property access of CqrsStepMetadata."""
    meta = CqrsStepMetadata(
        step_type="command",
        message_type="CreateOrderCommand",
        description="Creates a new customer order",
        requires_transaction=True,
    )

    step_type = meta.step_type
    msg_type = meta.message_type
    desc = meta.description
    req_tx = meta.requires_transaction

    assert step_type == "command"
    assert msg_type == "CreateOrderCommand"
    assert desc == "Creates a new customer order"
    assert req_tx is True


def test_cqrs_step_metadata_immutability() -> None:
    """Ensure CqrsStepMetadata is frozen and rejects mutation."""
    meta = CqrsStepMetadata(
        step_type="query",
        message_type="GetOrderQuery",
    )

    field_name = "step_type"
    with pytest.raises(ValidationError):
        setattr(meta, field_name, "command")


def test_cqrs_step_metadata_forbids_extra() -> None:
    """Ensure undeclared parameters are rejected by extra='forbid'."""
    with pytest.raises(ValidationError):
        data = {"step_type": "command", "message_type": "Cmd", "extra_field": "invalid"}
        CqrsStepMetadata(**data)


def test_workflow_execution_result_creation() -> None:
    """Validate construction of WorkflowExecutionResult value object."""
    now = datetime.now(UTC)
    result = WorkflowExecutionResult(
        run_id="run-101",
        workflow_name="order_flow",
        status="COMPLETED",
        completed_steps=("step_1", "step_2"),
        failed_steps=(),
        outputs={"step_2": {"order_id": "ord-1"}},
        started_at=now,
        ended_at=now,
        error_summary=None,
    )

    run_id = result.run_id
    status = result.status
    completed = result.completed_steps
    failed = result.failed_steps
    outputs = result.outputs

    assert run_id == "run-101"
    assert status == "COMPLETED"
    assert completed == ("step_1", "step_2")
    assert failed == ()
    assert outputs == {"step_2": {"order_id": "ord-1"}}
