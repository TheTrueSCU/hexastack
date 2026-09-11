"""Domain models, state machines, and status definitions for distributed sagas.

Notes/Architectural Intent:
    Provides pure domain representations of distributed transactions (Sagas) following the
    compensating transaction pattern. Contains no external dependencies or adapter concerns,
    enabling declarative multi-step workflows across bounded contexts.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from hexastack_core.domain.exceptions import HexastackError


class SagaStatus(StrEnum):
    """Execution lifecycle status of a distributed saga.

    Notes/Architectural Intent:
        Represents the state transitions of a saga from initial submission through
        successful completion or failure and compensation unwinding.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"


class SagaError(HexastackError):
    """Base exception for saga lifecycle, coordination, and execution failures.

    Notes/Architectural Intent:
        Specializes HexastackError for domain-level saga coordination failures.
    """


class SagaCompensationError(SagaError):
    """Exception raised when a compensating transaction fails during saga rollback.

    Notes/Architectural Intent:
        Signals an inconsistent or partially compensated state requiring manual operator
        intervention or dead-letter queue escalation.
    """


class SagaStep(BaseModel):
    """Definition of an individual step within a distributed saga.

    Notes/Architectural Intent:
        Pairs a forward transaction action with its compensating action. The action
        and compensation can be Command instances, callables, or factory functions.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    name: str = Field(description="Unique human-readable identifier for this step.")
    action: Any = Field(
        description="Forward command instance, command class, or action callable."
    )
    compensation: Any | None = Field(
        default=None,
        description="Compensating command instance, command class, or compensation callable.",
    )
    timeout_seconds: float | None = Field(
        default=None,
        description="Optional execution timeout bound for this step.",
    )


class SagaDefinition(BaseModel):
    """Complete specification of a multi-step distributed saga workflow.

    Notes/Architectural Intent:
        Immutable blueprint specifying the ordered sequence of SagaSteps and metadata.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    name: str = Field(description="Unique identifier name for this saga definition.")
    steps: tuple[SagaStep, ...] = Field(
        default_factory=tuple,
        description="Ordered sequence of forward and compensating steps.",
    )
    description: str = Field(
        default="",
        description="Optional architectural or business description of the saga.",
    )


class SagaState(BaseModel):
    """Runtime execution state tracking progress, results, and compensation stack.

    Notes/Architectural Intent:
        Mutable tracking model updated by saga orchestrators during forward execution
        and rollback phases.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    saga_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique execution identifier for this saga instance.",
    )
    saga_name: str = Field(description="Name of the executing saga definition.")
    status: SagaStatus = Field(
        default=SagaStatus.PENDING,
        description="Current execution lifecycle status.",
    )
    current_step_index: int = Field(
        default=0,
        description="Index of the currently executing or failing step.",
    )
    step_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary mapping step names to forward execution outputs.",
    )
    compensated_steps: list[str] = Field(
        default_factory=list,
        description="List of step names successfully compensated in reverse order.",
    )
    error: str | None = Field(
        default=None,
        description="Error message that triggered compensation or failure.",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when saga execution started.",
    )
    finished_at: datetime | None = Field(
        default=None,
        description="Timestamp when saga completed or terminated.",
    )


class SagaResult(BaseModel):
    """Immutable outcome of a saga execution returned to the caller.

    Notes/Architectural Intent:
        Provides callers with a clean status summary, step results, and fault diagnostics.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    saga_id: str = Field(description="Execution identifier.")
    saga_name: str = Field(description="Name of the saga definition.")
    status: SagaStatus = Field(description="Final terminal status.")
    step_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Forward execution outputs by step name.",
    )
    error: str | None = Field(
        default=None,
        description="Error diagnostics if saga did not complete successfully.",
    )
    compensated: bool = Field(
        default=False,
        description="True if compensations were successfully executed.",
    )
    compensated_steps: list[str] = Field(
        default_factory=list,
        description="List of step names successfully compensated in reverse order.",
    )
    execution_duration_ms: float = Field(
        default=0.0,
        description="Total duration in milliseconds.",
    )


__all__ = [
    "SagaCompensationError",
    "SagaDefinition",
    "SagaError",
    "SagaResult",
    "SagaState",
    "SagaStatus",
    "SagaStep",
]
