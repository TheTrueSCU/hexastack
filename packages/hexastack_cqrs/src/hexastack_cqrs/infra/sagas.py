"""Infrastructure builders and DSL for distributed saga definition and execution.

Notes/Architectural Intent:
    Provides a fluent SagaBuilder DSL for declaratively assembling multi-step sagas
    with forward actions, compensation triggers, and timeouts. Decouples saga configuration
    from orchestrator execution.
"""

from typing import Any, Self

from hexastack_cqrs.domain.sagas import (
    SagaDefinition,
    SagaStep,
)


class SagaBuilder:
    """Fluent declarative builder for constructing SagaDefinition instances.

    Notes/Architectural Intent:
        Enables clean, chainable registration of multi-step distributed workflows,
        pairing each forward action with its corresponding compensating transaction.
    """

    def __init__(self, name: str, description: str = "") -> None:
        """Initialize saga builder with name and optional description.

        Args:
            name: Unique identifier name for the saga workflow.
            description: Optional human-readable description of the workflow.
        """
        self._name = name
        self._description = description
        self._steps: list[SagaStep] = []

    def step(
        self,
        name: str,
        action: Any,
        compensate: Any | None = None,
        timeout_seconds: float | None = None,
    ) -> Self:
        """Append a forward and optional compensating step to the saga.

        Args:
            name: Unique name for this step.
            action: Command instance, command class, or forward callable.
            compensate: Optional compensating command instance, class, or rollback callable.
            timeout_seconds: Optional timeout bound in seconds for this step.

        Returns:
            Self for fluent method chaining.

        Raises:
            ValueError: If step name is empty or already registered in this builder.
        """
        if not name or not name.strip():
            raise ValueError("Saga step name cannot be empty.")

        if any(s.name == name for s in self._steps):
            raise ValueError(
                f"Saga step '{name}' is already registered in '{self._name}'."
            )

        self._steps.append(
            SagaStep(
                name=name,
                action=action,
                compensation=compensate,
                timeout_seconds=timeout_seconds,
            )
        )
        return self

    def build(self) -> SagaDefinition:
        """Build and validate an immutable SagaDefinition instance.

        Returns:
            The configured SagaDefinition.

        Raises:
            ValueError: If the saga has no steps registered.
        """
        if not self._steps:
            raise ValueError(f"Cannot build saga '{self._name}' with zero steps.")

        return SagaDefinition(
            name=self._name,
            steps=tuple(self._steps),
            description=self._description,
        )


def create_saga(name: str, description: str = "") -> SagaBuilder:
    """Factory helper creating a new SagaBuilder instance.

    Args:
        name: Unique identifier name for the saga.
        description: Optional description.

    Returns:
        New SagaBuilder instance ready for step chaining.
    """
    return SagaBuilder(name=name, description=description)


__all__ = [
    "create_saga",
    "SagaBuilder",
]
