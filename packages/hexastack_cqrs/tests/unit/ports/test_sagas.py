"""Unit tests for saga abstract ports.

Notes/Architectural Intent:
    Verifies that SagaOrchestratorPort and SagaStoragePort enforce abstractmethod contracts.
"""

import pytest

from hexastack_cqrs.domain.sagas import (
    SagaDefinition,
    SagaResult,
    SagaState,
    SagaStatus,
)
from hexastack_cqrs.ports.sagas import (
    SagaOrchestratorPort,
    SagaStoragePort,
)


def test_abstract_saga_orchestrator_port_cannot_be_instantiated():
    """Verify that SagaOrchestratorPort raises TypeError when instantiated directly."""
    with pytest.raises(TypeError):
        _ = SagaOrchestratorPort()  # type: ignore[abstract]


def test_abstract_saga_storage_port_cannot_be_instantiated():
    """Verify that SagaStoragePort raises TypeError when instantiated directly."""
    with pytest.raises(TypeError):
        _ = SagaStoragePort()  # type: ignore[abstract]


def test_concrete_saga_orchestrator_subclass_implements_interface():
    """Verify that a subclass implementing all methods satisfies SagaOrchestratorPort."""

    class ConcreteOrchestrator(SagaOrchestratorPort):
        def execute(self, saga: SagaDefinition, initial_state=None) -> SagaResult:
            return SagaResult(
                saga_id="mock-1",
                saga_name=saga.name,
                status=SagaStatus.COMPLETED,
            )

        async def execute_async(
            self, saga: SagaDefinition, initial_state=None
        ) -> SagaResult:
            return SagaResult(
                saga_id="mock-1-async",
                saga_name=saga.name,
                status=SagaStatus.COMPLETED,
            )

    orchestrator = ConcreteOrchestrator()
    definition = SagaDefinition(name="TestSaga")

    result = orchestrator.execute(definition)
    assert result.status == SagaStatus.COMPLETED
    assert result.saga_id == "mock-1"


def test_concrete_saga_storage_subclass_implements_interface():
    """Verify that a subclass implementing all methods satisfies SagaStoragePort."""

    class ConcreteStorage(SagaStoragePort):
        def __init__(self):
            self.store = {}

        def save_state(self, state: SagaState) -> None:
            self.store[state.saga_id] = state

        def get_state(self, saga_id: str) -> SagaState | None:
            return self.store.get(saga_id)

    storage = ConcreteStorage()
    state = SagaState(saga_id="s-1", saga_name="SampleSaga")
    storage.save_state(state)

    retrieved = storage.get_state("s-1")
    assert retrieved is not None
    assert retrieved.saga_name == "SampleSaga"
    assert storage.get_state("non-existent") is None
