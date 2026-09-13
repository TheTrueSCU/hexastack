"""Domain models and metadata descriptors for Hexastack flow execution.

Notes/Architectural Intent:
    Pure domain models defining CQRS-specific step metadata, execution results,
    and workflow run telemetry within the Hexastack framework. Free of database,
    HTTP, or external scheduler concerns.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CqrsStepMetadata",
    "WorkflowExecutionResult",
]


class CqrsStepMetadata(BaseModel):
    """Metadata descriptor for a CQRS command or query workflow step.

    Notes/Architectural Intent:
        Carried within StepDefinition.metadata to distinguish CQRS-driven steps
        from raw functions, providing dispatch target hints and schema contracts.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_type: str = Field(description="Step category: 'command' or 'query'.")
    message_type: str = Field(
        description="Qualified name or identifier of the dispatched message."
    )
    description: str = Field(
        default="", description="Optional architectural description of the step."
    )
    requires_transaction: bool = Field(
        default=True,
        description="Whether the step requires an enclosing UnitOfWork transaction.",
    )


class WorkflowExecutionResult(BaseModel):
    """Summary of a completed, suspended, or aborted workflow run.

    Notes/Architectural Intent:
        Immutable value object returned by workflow orchestrator ports, summarizing
        overall status, completed steps, outputs, and timing for CQRS callers.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(description="Unique workflow execution run identifier.")
    workflow_name: str = Field(description="Name of the executed workflow.")
    status: str = Field(
        description="Terminal or suspension status (e.g. COMPLETED, SUSPENDED)."
    )
    completed_steps: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Names of steps successfully evaluated.",
    )
    failed_steps: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Names of steps that encountered permanent errors.",
    )
    outputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Outputs produced by terminal or completed steps.",
    )
    started_at: datetime = Field(description="Timestamp when workflow run commenced.")
    ended_at: datetime = Field(
        description="Timestamp when workflow run finished or suspended."
    )
    error_summary: str | None = Field(
        default=None,
        description="Error details if workflow suspended or aborted.",
    )
