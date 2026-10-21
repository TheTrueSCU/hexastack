from abc import ABC, abstractmethod
from typing import Any

from hexastack_core.domain import Command, Generic, Query


class ExecutionPipelinePort(ABC):
    """Abstract interface defining CQRS execution pipeline operations.

    Notes/Architectural Intent:
        Establishes an inward-facing port for driving adapters (UI DevTools, HTTP controllers,
        CLI commands, AI agents) to dispatch and inspect CQRS messages without depending
        directly on concrete infrastructure pipeline and registry implementations (ADR-001).
    """

    @abstractmethod
    def execute(
        self,
        instance: Generic,
        output_format: str | None = None,
    ) -> Any:
        """Execute a Generic instance by routing to the appropriate bus and presenting output.

        Args:
            instance: Command, Query, Event, or Generic instance to execute.
            output_format: Optional target format ('json', 'dict', 'text', etc.).

        Returns:
            The presented or raw response data.

        Raises:
            PipelineError: If resolution, validation, or handler execution fails.
        """

    @abstractmethod
    def execute_by_name(
        self,
        name: str,
        payload: dict[str, Any],
        output_format: str | None = None,
    ) -> Any:
        """Instantiate and execute a registered Command or Query by string name and payload.

        Args:
            name: Registered class name identifier.
            payload: Parameter dictionary to validate into the message model.
            output_format: Optional presenter format string.

        Returns:
            The presented or raw execution result.

        Raises:
            PipelineError: If resolution or execution fails.
        """

    @abstractmethod
    def get_registered_commands(self) -> dict[str, type[Command]]:
        """Return a mapping of registered command names to their command classes.

        Returns:
            Dictionary mapping string names to Command classes.
        """

    @abstractmethod
    def get_registered_queries(self) -> dict[str, type[Query[Any]]]:
        """Return a mapping of registered query names to their query classes.

        Returns:
            Dictionary mapping string names to Query classes.
        """


__all__ = [
    "ExecutionPipelinePort",
]
