"""Unit tests for SagaBuilder and saga infrastructure helpers.

Notes/Architectural Intent:
    Verifies that SagaBuilder provides a fluent, validation-guarded DSL for assembling
    immutable SagaDefinition workflows.
"""

import pytest

from hexastack_cqrs.adapters.sagas.in_memory import InMemorySagaOrchestrator
from hexastack_cqrs.domain.sagas import SagaStatus
from hexastack_cqrs.infra.sagas import (
    SagaBuilder,
    create_saga,
)


def test_saga_builder_fluent_chaining_and_build():
    """Verify SagaBuilder constructs valid SagaDefinition with all step metadata."""
    saga = (
        SagaBuilder("TripBookingSaga", description="Book flight and hotel")
        .step(
            "BookFlight",
            action=lambda: "FL-100",
            compensate=lambda: "CancelFlight",
            timeout_seconds=10.0,
        )
        .step("ReserveHotel", action=lambda: "HT-200", compensate=lambda: "CancelHotel")
        .build()
    )

    assert saga.name == "TripBookingSaga"
    assert saga.description == "Book flight and hotel"
    assert len(saga.steps) == 2
    assert saga.steps[0].name == "BookFlight"
    assert saga.steps[0].timeout_seconds == 10.0
    assert saga.steps[1].name == "ReserveHotel"


def test_saga_builder_empty_name_raises_error():
    """Verify that registering a step with an empty name raises ValueError."""
    builder = SagaBuilder("TestSaga")
    with pytest.raises(ValueError, match="step name cannot be empty"):
        builder.step("", action=lambda: None)


def test_saga_builder_duplicate_step_name_raises_error():
    """Verify that registering duplicate step names within a saga raises ValueError."""
    builder = SagaBuilder("TestSaga")
    builder.step("StepA", action=lambda: None)
    with pytest.raises(ValueError, match="already registered"):
        builder.step("StepA", action=lambda: None)


def test_saga_builder_zero_steps_raises_error():
    """Verify that building a saga with zero registered steps raises ValueError."""
    builder = SagaBuilder("EmptySaga")
    with pytest.raises(ValueError, match="zero steps"):
        builder.build()


def test_create_saga_factory_helper():
    """Verify create_saga factory returns SagaBuilder and integrates with orchestrator."""
    trace: list[str] = []

    saga = (
        create_saga("FastSaga")
        .step("One", action=lambda: trace.append("one"))
        .step("Two", action=lambda: trace.append("two"))
        .build()
    )

    orchestrator = InMemorySagaOrchestrator()
    result = orchestrator.execute(saga)

    assert result.status == SagaStatus.COMPLETED
    assert trace == ["one", "two"]
