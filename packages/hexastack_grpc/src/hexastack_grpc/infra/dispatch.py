import inspect
from dataclasses import is_dataclass
from typing import Any

from hexastack_core.domain.command import Command
from hexastack_core.domain.query import Query
from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort
from pydantic import BaseModel
from rodi import Container


def _extract_dto_fields(request: Any, target_cls: type[Any]) -> dict[str, Any]:
    """Extract matching fields from a protobuf or dictionary request object."""
    data: dict[str, Any] = {}

    if hasattr(request, "DESCRIPTOR"):
        # Protobuf Message object
        for field in request.DESCRIPTOR.fields:
            data[field.name] = getattr(request, field.name)
    elif isinstance(request, dict):
        data = dict(request)
    else:
        # Fallback attribute copy
        if is_dataclass(target_cls):
            for f in target_cls.__dataclass_fields__:  # type: ignore[attr-defined]
                if hasattr(request, f):
                    data[f] = getattr(request, f)
        elif issubclass(target_cls, BaseModel):
            for f in target_cls.model_fields:
                if hasattr(request, f):
                    data[f] = getattr(request, f)

    return data


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
    fields = _extract_dto_fields(request, command_cls)
    fields.update(extra_kwargs)
    command = command_cls(**fields)
    bus = container.resolve(CommandBusPort)
    return bus.dispatch(command)  # type: ignore[return-value]


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
    fields = _extract_dto_fields(request, query_cls)
    fields.update(extra_kwargs)
    query = query_cls(**fields)
    bus = container.resolve(QueryBusPort)
    return bus.dispatch(query)  # type: ignore[return-value]


async def dispatch_rpc_command_async[C: Command, R](
    request: Any,
    command_cls: type[C],
    container: Container,
    **extra_kwargs: Any,
) -> R:
    """Asynchronously instantiate and dispatch a Command from a gRPC request."""
    fields = _extract_dto_fields(request, command_cls)
    fields.update(extra_kwargs)
    command = command_cls(**fields)
    bus = container.resolve(CommandBusPort)
    res = bus.dispatch(command)
    if inspect.isawaitable(res):
        res = await res
    return res  # type: ignore[return-value]


async def dispatch_rpc_query_async[Q: Query, R](
    request: Any,
    query_cls: type[Q],
    container: Container,
    **extra_kwargs: Any,
) -> R:
    """Asynchronously instantiate and dispatch a Query from a gRPC request."""
    fields = _extract_dto_fields(request, query_cls)
    fields.update(extra_kwargs)
    query = query_cls(**fields)
    bus = container.resolve(QueryBusPort)
    res = bus.dispatch(query)
    if inspect.isawaitable(res):
        res = await res
    return res  # type: ignore[return-value]


__all__ = [
    "dispatch_rpc_command",
    "dispatch_rpc_command_async",
    "dispatch_rpc_query",
    "dispatch_rpc_query_async",
]
