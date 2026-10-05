"""Unit tests for hexastack_flow domain events.

Notes/Architectural Intent:
    Validates construction and immutability of workflow lifecycle domain events.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from hexastack_flow.domain.events import (
    WorkflowAbortedEvent,
    WorkflowCompletedEvent,
    WorkflowStartedEvent,
    WorkflowStepCompletedEvent,
    WorkflowSuspendedEvent,
)


def test_workflow_started_event() -> None:
    """Validate WorkflowStartedEvent attributes."""
    now = datetime.now(UTC)
    evt = WorkflowStartedEvent(
        run_id="run-001",
        workflow_name="checkout",
        started_at=now,
    )

    run_id = evt.run_id
    wf_name = evt.workflow_name
    started = evt.started_at

    assert run_id == "run-001"
    assert wf_name == "checkout"
    assert started == now


def test_workflow_step_completed_event() -> None:
    """Validate WorkflowStepCompletedEvent attributes."""
    evt = WorkflowStepCompletedEvent(
        run_id="run-001",
        stage_name="payment",
        step_name="charge_card",
        attempt_number=1,
        duration_seconds=0.12,
        output_summary={"status": "PAID"},
    )

    step_name = evt.step_name
    attempt = evt.attempt_number
    output = evt.output_summary

    assert step_name == "charge_card"
    assert attempt == 1
    assert output == {"status": "PAID"}


def test_workflow_suspended_event() -> None:
    """Validate WorkflowSuspendedEvent attributes."""
    evt = WorkflowSuspendedEvent(
        run_id="run-001",
        stage_name="fulfillment",
        step_name="dispatch_courier",
        error_type="NetworkTimeoutError",
        error_message="Gateway connection refused",
    )

    stage = evt.stage_name
    err_type = evt.error_type
    err_msg = evt.error_message

    assert stage == "fulfillment"
    assert err_type == "NetworkTimeoutError"
    assert err_msg == "Gateway connection refused"


def test_workflow_completed_event() -> None:
    """Validate WorkflowCompletedEvent attributes."""
    now = datetime.now(UTC)
    evt = WorkflowCompletedEvent(
        run_id="run-001",
        workflow_name="checkout",
        completed_at=now,
        total_steps=4,
    )

    tot_steps = evt.total_steps
    assert tot_steps == 4


def test_workflow_aborted_event() -> None:
    """Validate WorkflowAbortedEvent attributes."""
    now = datetime.now(UTC)
    evt = WorkflowAbortedEvent(
        run_id="run-001",
        workflow_name="checkout",
        reason="Manual user cancellation",
        aborted_at=now,
    )

    reason = evt.reason
    assert reason == "Manual user cancellation"


def test_events_are_immutable() -> None:
    """Ensure events are frozen."""
    evt = WorkflowStartedEvent(
        run_id="run-001",
        workflow_name="checkout",
        started_at=datetime.now(UTC),
    )

    field_name = "run_id"
    with pytest.raises(ValidationError):
        setattr(evt, field_name, "new-id")
