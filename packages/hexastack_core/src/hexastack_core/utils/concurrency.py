"""Type-safe sync/async concurrency bridging utilities.

Notes/Architectural Intent:
    Provides structured concurrency and ergonomic sync/async bridging across Hexastack
    pipelines without blocking the event loop or losing context variables.
    Integrates `asyncer` (built on `anyio`) with transparent fallback to `asyncio.to_thread`
    with contextvars propagation when running in minimal environments.
"""

from __future__ import annotations

import asyncio
import contextvars
import functools
import inspect
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, cast

from hexastack_core.utils.imports import optional_dependency, require_dependency

__all__ = [
    "asyncify",
    "create_task_group",
    "is_coroutine_callable",
    "runnify",
    "syncify",
]


def is_coroutine_callable(fn: Any) -> bool:
    """Return True if fn is an async coroutine function or callable object.

    Args:
        fn: Any function, method, or callable object to inspect.

    Returns:
        True if fn is a coroutine function or defines an async __call__ method.

    Notes/Architectural Intent:
        Unwraps partials and decorators (`__wrapped__`) to detect async coroutine handlers
        reliably before deciding whether to dispatch on the event loop or worker thread pool.
    """
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__

    if inspect.iscoroutinefunction(fn):
        return True

    if callable(fn):
        return inspect.iscoroutinefunction(type(fn).__call__)

    return False


def asyncify[**P, R](
    function: Callable[P, R],
    *,
    abandon_on_cancel: bool = False,
    cancellable: bool | None = None,
    limiter: Any = None,
) -> Callable[P, Awaitable[R]]:
    """Convert a synchronous function into an asynchronous awaitable running on a worker thread.

    Args:
        function: Synchronous callable to offload to worker thread.
        abandon_on_cancel: Whether to abandon thread execution if cancelled (asyncer only).
        cancellable: Optional cancellation flag passed to anyio (asyncer only).
        limiter: Optional concurrency capacity limiter (asyncer only).

    Returns:
        Asynchronous wrapper returning an Awaitable resolving to the function's return value.

    Notes/Architectural Intent:
        Preserves active context variables (correlation IDs, tenant contexts, OpenTelemetry spans)
        across the thread hop, preventing event-loop starvation during blocking I/O operations.
    """
    asyncer = optional_dependency("asyncer")
    if asyncer is not None:
        return asyncer.asyncify(  # type: ignore[no-any-return]
            function,
            abandon_on_cancel=abandon_on_cancel,
            cancellable=cancellable,
            limiter=limiter,
        )

    from hexastack_core.utils.runtime import supports_threads

    if not supports_threads():

        @functools.wraps(function)
        async def _cooperative_fallback(*args: P.args, **kwargs: P.kwargs) -> R:
            return function(*args, **kwargs)

        return _cooperative_fallback

    @functools.wraps(function)
    async def _async_fallback(*args: P.args, **kwargs: P.kwargs) -> R:
        ctx = contextvars.copy_context()
        return cast("R", await asyncio.to_thread(ctx.run, function, *args, **kwargs))

    return _async_fallback


def syncify[**P, R](
    async_function: Callable[P, Coroutine[Any, Any, R]],
    *,
    raise_sync_error: bool = True,
) -> Callable[P, R]:
    """Convert an asynchronous coroutine function into a synchronous callable.

    Args:
        async_function: Asynchronous coroutine function to execute synchronously.
        raise_sync_error: Whether to raise an error if invoked outside an async context.

    Returns:
        Synchronous callable returning R.

    Raises:
        MissingDependencyError: If optional dependency `asyncer` is not installed.

    Notes/Architectural Intent:
        Allows synchronous service adapters or command handlers executing within a worker thread
        to cleanly invoke asynchronous ports via an AnyIO portal without deadlocking the loop.
    """
    asyncer = require_dependency(
        "asyncer",
        extra="async",
        package="hexastack-core",
        feature_name="syncify",
    )
    return asyncer.syncify(  # type: ignore[no-any-return]
        async_function,
        raise_sync_error=raise_sync_error,
    )


def create_task_group() -> Any:
    """Create a structured concurrency task group.

    Returns:
        Structured TaskGroup context manager.

    Raises:
        MissingDependencyError: If optional dependency `asyncer` is not installed.

    Notes/Architectural Intent:
        Enforces structured concurrency boundaries across asynchronous workers,
        ensuring all child tasks complete or cancel cleanly before exiting the group block.
    """
    asyncer = require_dependency(
        "asyncer",
        extra="async",
        package="hexastack-core",
        feature_name="create_task_group",
    )
    return asyncer.create_task_group()


def runnify[**P, R](
    async_function: Callable[P, Coroutine[Any, Any, R]],
) -> Callable[P, R]:
    """Create a synchronous runner for an asynchronous coroutine function.

    Args:
        async_function: Asynchronous coroutine function.

    Returns:
        Synchronous callable that invokes the coroutine to completion via an event loop.

    Notes/Architectural Intent:
        Provides an ergonomic bridge for driving synchronous CLI entrypoints and test harnesses
        from asynchronous domain engines.
    """
    asyncer = optional_dependency("asyncer")
    if asyncer is not None:
        return asyncer.runnify(async_function)  # type: ignore[no-any-return]

    @functools.wraps(async_function)
    def _runnify_fallback(*args: P.args, **kwargs: P.kwargs) -> R:
        return asyncio.run(async_function(*args, **kwargs))

    return _runnify_fallback
