"""Event publishing adapter broadcasting workflow state transitions.

Notes/Architectural Intent:
    Connects workflow engine state transitions to Hexastack event buses,
    allowing distributed subscribers or local event handlers to react to
    workflow progress, suspension, or completion.
"""

from datetime import UTC, datetime
from typing import Any

from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_flow.domain.events import (
    WorkflowAbortedEvent,
    WorkflowCompletedEvent,
    WorkflowStartedEvent,
    WorkflowStepCompletedEvent,
    WorkflowSuspendedEvent,
)

__all__ = [
    "WorkflowEventPublisher",
]


class WorkflowEventPublisher:
    """Publisher broadcasting workflow domain events to an EventBusPort.

    Notes/Architectural Intent:
        Encapsulates construction and dispatching of domain events across
        in-process or distributed event buses.
    """

    def __init__(self, event_bus: EventBusPort) -> None:
        """Initialize publisher with an event bus.

        Args:
            event_bus: The EventBusPort to publish events through.
        """
        self._bus = event_bus

    def publish_started(self, run_id: str, workflow_name: str) -> None:
        """Broadcast WorkflowStartedEvent.

        Args:
            run_id: Workflow execution run identifier.
            workflow_name: Name of the workflow definition.
        """
        event = WorkflowStartedEvent(
            run_id=run_id,
            workflow_name=workflow_name,
            started_at=datetime.now(UTC),
        )
        self._bus.publish(event)

    def publish_step_completed(
        self,
        run_id: str,
        stage_name: str,
        step_name: str,
        attempt_number: int,
        duration_seconds: float,
        output_summary: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast WorkflowStepCompletedEvent.

        Args:
            run_id: Workflow execution run identifier.
            stage_name: Enclosing stage name.
            step_name: Name of the completed step.
            attempt_number: Attempt count.
            duration_seconds: Step execution time in seconds.
            output_summary: Optional dictionary summarizing key output values.
        """
        event = WorkflowStepCompletedEvent(
            run_id=run_id,
            stage_name=stage_name,
            step_name=step_name,
            attempt_number=attempt_number,
            duration_seconds=duration_seconds,
            output_summary=output_summary or {},
        )
        self._bus.publish(event)

    def publish_suspended(
        self,
        run_id: str,
        stage_name: str,
        step_name: str,
        error_type: str,
        error_message: str,
    ) -> None:
        """Broadcast WorkflowSuspendedEvent.

        Args:
            run_id: Workflow execution run identifier.
            stage_name: Stage where suspension occurred.
            step_name: Step that failed permanently.
            error_type: Exception class name.
            error_message: Human-readable error description.
        """
        event = WorkflowSuspendedEvent(
            run_id=run_id,
            stage_name=stage_name,
            step_name=step_name,
            error_type=error_type,
            error_message=error_message,
        )
        self._bus.publish(event)

    def publish_completed(
        self,
        run_id: str,
        workflow_name: str,
        total_steps: int,
    ) -> None:
        """Broadcast WorkflowCompletedEvent.

        Args:
            run_id: Workflow execution run identifier.
            workflow_name: Name of the completed workflow.
            total_steps: Total count of steps evaluated.
        """
        event = WorkflowCompletedEvent(
            run_id=run_id,
            workflow_name=workflow_name,
            completed_at=datetime.now(UTC),
            total_steps=total_steps,
        )
        self._bus.publish(event)

    def publish_aborted(
        self,
        run_id: str,
        workflow_name: str,
        reason: str,
    ) -> None:
        """Broadcast WorkflowAbortedEvent.

        Args:
            run_id: Workflow execution run identifier.
            workflow_name: Name of the aborted workflow.
            reason: Cancellation reason description.
        """
        event = WorkflowAbortedEvent(
            run_id=run_id,
            workflow_name=workflow_name,
            reason=reason,
            aborted_at=datetime.now(UTC),
        )
        self._bus.publish(event)
