"""CQRS dispatch helpers for NiceGUI reactive event handlers.

Notes/Architectural Intent:
    Allows NiceGUI buttons, form submissions, and reactive event loops to invoke
    ExecutionPipeline commands and queries synchronously or asynchronously.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hexastack_core.domain import Command, Query
    from hexastack_cqrs.ports.pipeline import ExecutionPipelinePort

__all__ = [
    "dispatch_command",
    "dispatch_query",
]


async def dispatch_command(pipeline: ExecutionPipelinePort, command: Command) -> Any:
    """Dispatch a CQRS command from a NiceGUI interactive event handler.

    Args:
        pipeline: ExecutionPipelinePort instance.
        command: Command instance to execute.

    Returns:
        Result returned by command execution.

    Raises:
        Exception: Propagates any handler or middleware execution errors.

    Notes/Architectural Intent:
        Executes a command through the standard ExecutionPipelinePort,
        transparently awaiting async handler returns or returning synchronous values.
    """
    result = pipeline.execute(command)
    if inspect.isawaitable(result):
        return await result
    return result


async def dispatch_query(pipeline: ExecutionPipelinePort, query: Query) -> Any:
    """Dispatch a CQRS query from a NiceGUI interactive event handler or data loader.

    Args:
        pipeline: ExecutionPipelinePort instance.
        query: Query instance to execute.

    Returns:
        Result returned by query execution.

    Raises:
        Exception: Propagates any query handler execution errors.

    Notes/Architectural Intent:
        Executes a query through the standard ExecutionPipeline,
        transparently awaiting async handler returns or returning synchronous values.
    """
    result = pipeline.execute(query)
    if inspect.isawaitable(result):
        return await result
    return result
