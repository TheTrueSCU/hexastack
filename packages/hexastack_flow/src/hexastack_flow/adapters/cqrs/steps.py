"""CQRS Command and Query adapters for hexaflow steps.

Notes/Architectural Intent:
    Bridges hexaflow StepDefinition callables directly to Hexastack CommandBusPort
    and QueryBusPort. Enables declarative execution of typed domain commands
    within workflow DAGs, automatically inheriting the full CQRS middleware chain.
"""

from collections.abc import Callable
from typing import Any

from hexaflow.domain.models import StepDefinition
from hexaflow.domain.state import StepContext

from hexastack_core.domain import Command, Query
from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort
from hexastack_flow.domain.models import CqrsStepMetadata

__all__ = [
    "as_command_step",
    "as_query_step",
    "CommandStep",
    "QueryStep",
]


class CommandStep:
    """Step action adapter dispatching a domain Command via CommandBusPort.

    Notes/Architectural Intent:
        Callable step action that takes StepContext, extracts inputs to construct
        a typed Command instance, and dispatches it through the CommandBus.
    """

    def __init__(
        self,
        command_factory: Callable[[StepContext], Command],
        command_bus: CommandBusPort,
    ) -> None:
        """Initialize CommandStep with command factory and bus.

        Args:
            command_factory: Callable receiving StepContext and producing a Command.
            command_bus: CommandBusPort implementation for dispatching.
        """
        self._factory = command_factory
        self._bus = command_bus

    def __call__(self, ctx: StepContext) -> Any:
        """Execute step by creating and dispatching the domain Command.

        Args:
            ctx: Runtime StepContext provided by hexaflow engine.

        Returns:
            The result returned by the registered command handler.

        Raises:
            Exception: Propagates handler execution or validation errors.
        """
        command = self._factory(ctx)
        return self._bus.dispatch(command)


class QueryStep:
    """Step action adapter dispatching a domain Query via QueryBusPort.

    Notes/Architectural Intent:
        Callable step action that takes StepContext, constructs a typed Query,
        and retrieves data via QueryBus, making query results available to downstream steps.
    """

    def __init__(
        self,
        query_factory: Callable[[StepContext], Query[Any]],
        query_bus: QueryBusPort,
    ) -> None:
        """Initialize QueryStep with query factory and bus.

        Args:
            query_factory: Callable receiving StepContext and producing a Query.
            query_bus: QueryBusPort implementation for dispatching.
        """
        self._factory = query_factory
        self._bus = query_bus

    def __call__(self, ctx: StepContext) -> Any:
        """Execute step by creating and dispatching the domain Query.

        Args:
            ctx: Runtime StepContext provided by hexaflow engine.

        Returns:
            The query result returned by the registered query handler.

        Raises:
            Exception: Propagates query handler execution errors.
        """
        query = self._factory(ctx)
        return self._bus.dispatch(query)


def as_command_step(
    name: str,
    command_factory: Callable[[StepContext], Command],
    command_bus: CommandBusPort,
    depends_on: tuple[str, ...] = (),
    compensation_factory: Callable[[StepContext], Command] | None = None,
    description: str = "",
    timeout_seconds: float | None = None,
) -> StepDefinition:
    """Construct a hexaflow StepDefinition backed by a CommandStep.

    Args:
        name: Unique step identifier name.
        command_factory: Callable producing the domain Command from StepContext.
        command_bus: CommandBusPort to dispatch through.
        depends_on: Prerequisites for join barrier synchronization.
        compensation_factory: Optional compensating command factory for rollbacks.
        description: Architectural description of the step.
        timeout_seconds: Maximum allowed execution seconds.

    Returns:
        Configured hexaflow StepDefinition with attached CqrsStepMetadata.

    Raises:
        ValueError: If name is empty.
    """
    if not name:
        raise ValueError("Step name must not be empty.")

    action = CommandStep(command_factory, command_bus)
    compensation = (
        CommandStep(compensation_factory, command_bus)
        if compensation_factory is not None
        else None
    )

    metadata = {
        "cqrs": CqrsStepMetadata(
            step_type="command",
            message_type=name,
            description=description,
        ).model_dump(),
    }

    return StepDefinition(
        name=name,
        action=action,
        compensation=compensation,
        depends_on=depends_on,
        timeout_seconds=timeout_seconds,
        metadata=metadata,
    )


def as_query_step(
    name: str,
    query_factory: Callable[[StepContext], Query[Any]],
    query_bus: QueryBusPort,
    depends_on: tuple[str, ...] = (),
    description: str = "",
    timeout_seconds: float | None = None,
) -> StepDefinition:
    """Construct a hexaflow StepDefinition backed by a QueryStep.

    Args:
        name: Unique step identifier name.
        query_factory: Callable producing the domain Query from StepContext.
        query_bus: QueryBusPort to dispatch through.
        depends_on: Prerequisites for join barrier synchronization.
        description: Architectural description of the step.
        timeout_seconds: Maximum allowed execution seconds.

    Returns:
        Configured hexaflow StepDefinition with attached CqrsStepMetadata.

    Raises:
        ValueError: If name is empty.
    """
    if not name:
        raise ValueError("Step name must not be empty.")

    action = QueryStep(query_factory, query_bus)
    metadata = {
        "cqrs": CqrsStepMetadata(
            step_type="query",
            message_type=name,
            description=description,
            requires_transaction=False,
        ).model_dump(),
    }

    return StepDefinition(
        name=name,
        action=action,
        depends_on=depends_on,
        timeout_seconds=timeout_seconds,
        metadata=metadata,
    )
