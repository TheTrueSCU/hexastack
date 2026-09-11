"""Unit tests for saga domain models, statuses, and exceptions.

Notes/Architectural Intent:
    Verifies that SagaStatus, SagaStep, SagaDefinition, SagaState, and SagaResult
    behave deterministically according to hexagonal domain invariants.
"""

from hexastack_core.domain.command import Command
from hexastack_cqrs.domain.sagas import (
    SagaCompensationError,
    SagaDefinition,
    SagaError,
    SagaResult,
    SagaState,
    SagaStatus,
    SagaStep,
)


class DummyCommand(Command):
    item_id: str


def test_saga_status_enum_values():
    """Verify all lifecycle enum states exist and have string representations."""
    assert SagaStatus.PENDING == "PENDING"
    assert SagaStatus.RUNNING == "RUNNING"
    assert SagaStatus.COMPLETED == "COMPLETED"
    assert SagaStatus.COMPENSATING == "COMPENSATING"
    assert SagaStatus.COMPENSATED == "COMPENSATED"
    assert SagaStatus.FAILED == "FAILED"


def test_saga_step_instantiation_and_immutability():
    """Verify SagaStep model validation and frozen config."""
    step = SagaStep(
        name="Step1",
        action=DummyCommand,
        compensation=DummyCommand,
        timeout_seconds=5.0,
    )
    assert step.name == "Step1"
    assert step.action is DummyCommand
    assert step.compensation is DummyCommand
    assert step.timeout_seconds == 5.0


def test_saga_definition():
    """Verify SagaDefinition structure and step collection."""
    step1 = SagaStep(name="Step1", action="action1", compensation="comp1")
    step2 = SagaStep(name="Step2", action="action2", compensation=None)

    definition = SagaDefinition(
        name="TripBookingSaga",
        steps=(step1, step2),
        description="Coordinates trip reservations",
    )

    assert definition.name == "TripBookingSaga"
    assert len(definition.steps) == 2
    assert definition.steps[0].name == "Step1"
    assert definition.steps[1].compensation is None
    assert definition.description == "Coordinates trip reservations"


def test_saga_state_lifecycle():
    """Verify SagaState mutable tracking throughout execution lifecycle."""
    state = SagaState(saga_name="OrderSaga")

    assert state.saga_name == "OrderSaga"
    assert state.status == SagaStatus.PENDING
    assert state.current_step_index == 0
    assert len(state.step_results) == 0
    assert len(state.compensated_steps) == 0
    assert state.error is None
    assert state.started_at is not None
    assert state.finished_at is None

    # Mutate state during simulation
    state.status = SagaStatus.RUNNING
    state.step_results["Step1"] = {"reservation_id": "res-123"}
    state.current_step_index = 1
    state.status = SagaStatus.COMPENSATING
    state.compensated_steps.append("Step1")
    state.error = "Car inventory exhausted"
    state.status = SagaStatus.COMPENSATED

    assert state.status == SagaStatus.COMPENSATED
    assert state.step_results["Step1"]["reservation_id"] == "res-123"
    assert state.compensated_steps == ["Step1"]
    assert state.error == "Car inventory exhausted"


def test_saga_result_immutability():
    """Verify SagaResult properties and immutability."""
    result = SagaResult(
        saga_id="saga-xyz",
        saga_name="TripSaga",
        status=SagaStatus.COMPLETED,
        step_results={"flight": "FL-101", "hotel": "HT-202"},
        compensated=False,
        execution_duration_ms=42.5,
    )

    assert result.saga_id == "saga-xyz"
    assert result.saga_name == "TripSaga"
    assert result.status == SagaStatus.COMPLETED
    assert result.step_results["flight"] == "FL-101"
    assert result.compensated is False
    assert result.execution_duration_ms == 42.5
    assert result.error is None


def test_saga_exceptions_hierarchy():
    """Verify saga exception class inheritance and diagnostics."""
    base_err = SagaError("Coordination error")
    assert isinstance(base_err, Exception)
    assert str(base_err) == "Coordination error"

    comp_err = SagaCompensationError("Failed to refund payment")
    assert isinstance(comp_err, SagaError)
    assert "Failed to refund payment" in str(comp_err)
