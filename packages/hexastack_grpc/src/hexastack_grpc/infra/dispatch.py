import inspect
from typing import Any

from rodi import Container

from hexastack_core.domain.command import Command
from hexastack_core.domain.query import Query
from hexastack_core.utils.inspection import extract_dto_fields
from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort

__all__ = [
    "dispatch_rpc_command",
    "dispatch_rpc_command_async",
    "dispatch_rpc_query",
    "dispatch_rpc_query_async",
]


def dispatch_rpc_command[C: Command, R](
    request: Any,
    command_cls: type[C],
    container: Container,
    **extra_kwargs: Any,
) -> R:
    """Instantiate and dispatch a Command from a gRPC protobuf request.

    Notes/Architectural Intent:
        Bridges gRPC RPC handlers to CQRS CommandBusPort with automatic field mapping.

    Args:
        request: Incoming Protobuf request object.
        command_cls: Target Command DTO class.
        container: Active rodi DI Container.
        **extra_kwargs: Additional parameters overriding request fields.

    Returns:
        Command execution result.
    """
    fields = extract_dto_fields(request, command_cls)
    fields.update(extra_kwargs)
    command = command_cls(**fields)
    bus = container.resolve(CommandBusPort)
    return bus.dispatch(command)  # type: ignore[return-value]


async def dispatch_rpc_command_async[C: Command, R](
    request: Any,
    command_cls: type[C],
    container: Container,
    **extra_kwargs: Any,
) -> R:
    """Asynchronously instantiate and dispatch a Command from a gRPC request."""
    fields = extract_dto_fields(request, command_cls)
    fields.update(extra_kwargs)
    command = command_cls(**fields)
    bus = container.resolve(CommandBusPort)
    res = bus.dispatch(command)
    if inspect.isawaitable(res):
        res = await res
    return res  # type: ignore[return-value]


def dispatch_rpc_query[Q: Query, R](
    request: Any,
    query_cls: type[Q],
    container: Container,
    **extra_kwargs: Any,
) -> R:
    """Instantiate and dispatch a Query from a gRPC protobuf request.

    Args:
        request: Incoming Protobuf request object.
        query_cls: Target Query DTO class.
        container: Active rodi DI Container.
        **extra_kwargs: Additional parameters overriding request fields.

    Returns:
        Query execution result.
    """
    fields = extract_dto_fields(request, query_cls)
    fields.update(extra_kwargs)
    query = query_cls(**fields)
    bus = container.resolve(QueryBusPort)
    return bus.dispatch(query)  # type: ignore[return-value]


async def dispatch_rpc_query_async[Q: Query, R](
    request: Any,
    query_cls: type[Q],
    container: Container,
    **extra_kwargs: Any,
) -> R:
    """Asynchronously instantiate and dispatch a Query from a gRPC request."""
    fields = extract_dto_fields(request, query_cls)
    fields.update(extra_kwargs)
    query = query_cls(**fields)
    bus = container.resolve(QueryBusPort)
    res = bus.dispatch(query)
    if inspect.isawaitable(res):
        res = await res
    return res  # type: ignore[return-value]
