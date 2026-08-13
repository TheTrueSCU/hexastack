from hexastack_core.domain.command import Command
from hexastack_core.domain.query import Query
from strawberry.types import Info

from hexastack_graphql.domain.context import GraphQLContext
from hexastack_graphql.domain.exceptions import GraphQLError


def dispatch_query[T](
    info: Info[GraphQLContext, None],
    query: Query,
) -> T:
    """Dispatch a CQRS query from inside a Strawberry field resolver.

    Notes/Architectural Intent:
        Resolves QueryBusPort from info.context and dispatches the query,
        returning the handler's result with type inference.

    Args:
        info: Strawberry execution Info object containing GraphQLContext.
        query: Concrete Query instance to dispatch.

    Returns:
        The query execution result.

    Raises:
        GraphQLError: If QueryBusPort is not configured in context.
    """
    bus = info.context.query_bus
    if bus is None:
        raise GraphQLError(
            "QueryBusPort is not available in GraphQLContext. "
            "Ensure hexastack-cqrs is configured."
        )
    return bus.dispatch(query)  # type: ignore[no-any-return]


def dispatch_command[T](
    info: Info[GraphQLContext, None],
    command: Command,
) -> T:
    """Dispatch a CQRS command from inside a Strawberry field resolver.

    Notes/Architectural Intent:
        Resolves CommandBusPort from info.context and dispatches the command,
        returning the handler's result with type inference.

    Args:
        info: Strawberry execution Info object containing GraphQLContext.
        command: Concrete Command instance to dispatch.

    Returns:
        The command execution result.

    Raises:
        GraphQLError: If CommandBusPort is not configured in context.
    """
    bus = info.context.command_bus
    if bus is None:
        raise GraphQLError(
            "CommandBusPort is not available in GraphQLContext. "
            "Ensure hexastack-cqrs is configured."
        )
    return bus.dispatch(command)  # type: ignore[no-any-return]


__all__ = [
    "dispatch_command",
    "dispatch_query",
]
