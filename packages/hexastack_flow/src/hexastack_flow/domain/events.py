"""Domain events emitted during workflow lifecycle state transitions.

Notes/Architectural Intent:
    Pure domain events capturing facts about workflow progress: commencement,
    step completion, suspension on permanent failure, completion, and abort.
    Subclasses hexastack_core.domain.Event to seamlessly integrate with
    hexastack-events and CQRS EventBusPort.
"""

from datetime import datetime
from typing import Any

from pydantic import Field

from hexastack_core.domain import Event

__all__ = [
    "WorkflowAbortedEvent",
    "WorkflowCompletedEvent",
    "WorkflowStartedEvent",
    "WorkflowStepCompletedEvent",
    "WorkflowSuspendedEvent",
]


class WorkflowStartedEvent(Event):
    """Event emitted when a workflow run transitions to RUNNING.

    Notes/Architectural Intent:
        Signals downstream listeners that execution has commenced for run_id.
    """

    run_id: str = Field(description="Unique workflow run identifier.")
    workflow_name: str = Field(description="Name of the workflow definition.")
    started_at: datetime = Field(description="Timestamp when execution began.")


class WorkflowStepCompletedEvent(Event):
    """Event emitted when an individual workflow step completes successfully.

    Notes/Architectural Intent:
        Emitted upon checkpoint commit, allowing event-driven telemetry and
        asynchronous outbox publishing without stalling the engine.
    """

    run_id: str = Field(description="Unique workflow run identifier.")
    stage_name: str = Field(description="Name of the enclosing stage.")
    step_name: str = Field(description="Name of the completed step.")
    attempt_number: int = Field(description="Attempt count that succeeded.")
    duration_seconds: float = Field(description="Execution duration in seconds.")
    output_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Key output fields or metadata produced by step.",
    )


class WorkflowSuspendedEvent(Event):
    """Event emitted when a workflow run suspends due to permanent step failure.

    Notes/Architectural Intent:
        Alerts operator consoles or dead-letter monitors that human intervention
        or external correction is required to resume the run.
    """

    run_id: str = Field(description="Unique workflow run identifier.")
    stage_name: str = Field(description="Stage where suspension occurred.")
    step_name: str = Field(description="Step that failed permanently.")
    error_type: str = Field(description="Qualified exception class name.")
    error_message: str = Field(description="Human-readable exception message.")


class WorkflowCompletedEvent(Event):
    """Event emitted when all stages and steps in a workflow reach COMPLETED.

    Notes/Architectural Intent:
        Signals terminal completion of the multi-step business process.
    """

    run_id: str = Field(description="Unique workflow run identifier.")
    workflow_name: str = Field(description="Name of the completed workflow.")
    completed_at: datetime = Field(description="Timestamp of workflow completion.")
    total_steps: int = Field(description="Total number of evaluated steps.")


class WorkflowAbortedEvent(Event):
    """Event emitted when a suspended workflow is explicitly cancelled with rollback.

    Notes/Architectural Intent:
        Records that compensating actions were executed and the workflow was halted.
    """

    run_id: str = Field(description="Unique workflow run identifier.")
    workflow_name: str = Field(description="Name of the aborted workflow.")
    reason: str = Field(description="Operator rationale or cancellation reason.")
    aborted_at: datetime = Field(description="Timestamp of abort execution.")
