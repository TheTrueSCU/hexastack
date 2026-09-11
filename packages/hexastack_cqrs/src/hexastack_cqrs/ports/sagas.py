"""Abstract ports defining distributed saga orchestration and persistence interfaces.

Notes/Architectural Intent:
    Establishes inward-facing contracts for orchestrating multi-step sagas across bounded
    contexts with automated compensating transaction unwinding. Decouples the application
    core from in-memory or external workflow coordinators (e.g. Temporal).
"""

from abc import ABC, abstractmethod
from typing import Any

from hexastack_cqrs.domain.sagas import (
    SagaDefinition,
    SagaResult,
    SagaState,
)


class SagaOrchestratorPort(ABC):
    """Abstract port for coordinating and executing distributed sagas.

    Notes/Architectural Intent:
        Defines the execution lifecycle contract for saga coordinators, supporting
        both synchronous in-process execution and asynchronous distributed execution.
    """

    @abstractmethod
    def execute(
        self,
        saga: SagaDefinition,
        initial_state: dict[str, Any] | None = None,
    ) -> SagaResult:
        """Execute a saga definition synchronously with optional initial context.

        Args:
            saga: The immutable SagaDefinition specification to execute.
            initial_state: Optional dictionary containing initial input parameters.

        Returns:
            SagaResult indicating COMPLETED or COMPENSATED/FAILED outcome.

        Raises:
            SagaError: If coordination encounters an unrecoverable failure.
        """

    @abstractmethod
    async def execute_async(
        self,
        saga: SagaDefinition,
        initial_state: dict[str, Any] | None = None,
    ) -> SagaResult:
        """Execute a saga definition asynchronously with optional initial context.

        Args:
            saga: The immutable SagaDefinition specification to execute.
            initial_state: Optional dictionary containing initial input parameters.

        Returns:
            SagaResult indicating COMPLETED or COMPENSATED/FAILED outcome.

        Raises:
            SagaError: If coordination encounters an unrecoverable failure.
        """


class SagaStoragePort(ABC):
    """Abstract port for persisting and retrieving saga execution states.

    Notes/Architectural Intent:
        Enables durable saga coordinators to checkpoint step progress and resume
        or compensate after system restarts or worker crashes.
    """

    @abstractmethod
    def save_state(self, state: SagaState) -> None:
        """Persist or update the state of an active or completed saga.

        Args:
            state: The SagaState snapshot to store.
        """

    @abstractmethod
    def get_state(self, saga_id: str) -> SagaState | None:
        """Retrieve the persisted execution state of a saga by ID.

        Args:
            saga_id: Unique saga execution identifier.

        Returns:
            The stored SagaState, or None if not found.
        """


__all__ = [
    "SagaOrchestratorPort",
    "SagaStoragePort",
]
