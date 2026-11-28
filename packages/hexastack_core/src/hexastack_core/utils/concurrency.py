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
from collections.abc import Awaitable, Callable, Collection, Coroutine
from typing import Any, Protocol, cast, overload

from hexastack_core.utils.imports import optional_dependency, require_dependency
from hexastack_core.utils.runtime import supports_threads

__all__ = [
    "asyncify",
    "auto_async",
    "create_task_group",
    "is_coroutine_callable",
    "runnify",
    "syncify",
    "to_async",
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


def _build_async_wrapper[**P, R](
    fn: Callable[P, R],
    *,
    async_name: str | None = None,
    async_qualname: str | None = None,
) -> Callable[P, Coroutine[Any, Any, R]]:
    @functools.wraps(fn)
    async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
        if not supports_threads():
            return fn(*args, **kwargs)
        ctx = contextvars.copy_context()
        return await asyncio.to_thread(ctx.run, fn, *args, **kwargs)

    if async_name is not None:
        _async_wrapper.__name__ = async_name
    if async_qualname is not None:
        _async_wrapper.__qualname__ = async_qualname
    return cast("Callable[P, Coroutine[Any, Any, R]]", _async_wrapper)


def to_async[**P, R](
    fn: Callable[P, R],
) -> Callable[P, Coroutine[Any, Any, R]]:
    """Convert a synchronous callable into a thread-offloaded async coroutine function.

    Args:
        fn: Synchronous function or boundable method to execute without blocking the event loop.

    Returns:
        Coroutine function preserving parameter types, return type, metadata, and context variables.

    Notes/Architectural Intent:
        Produces a native ``async def`` coroutine function (unlike generic Awaitable wrappers)
        so descriptor binding works transparently on class methods and ``inspect.iscoroutinefunction``
        returns True. Automatically copies active ``contextvars`` across worker thread boundaries and
        falls back to cooperative in-loop execution when threads are unsupported (ADR-016).
    """
    if inspect.iscoroutinefunction(fn):
        return cast("Callable[P, Coroutine[Any, Any, R]]", fn)

    return _build_async_wrapper(fn)


class _ClassDecorator(Protocol):
    def __call__[T: type](self, cls: T, /) -> T:
        """Attach synthesized async twins to ``cls`` and return it."""


def _replace_qualname(qualname: str, new_name: str) -> str:
    if "." in qualname:
        prefix, _ = qualname.rsplit(".", 1)
        return f"{prefix}.{new_name}"
    return new_name


def _make_async_twin(
    sync_fn: Callable[..., Any],
    async_name: str,
) -> Callable[..., Coroutine[Any, Any, Any]]:
    orig_qualname = getattr(sync_fn, "__qualname__", async_name)
    return _build_async_wrapper(
        sync_fn,
        async_name=async_name,
        async_qualname=_replace_qualname(orig_qualname, async_name),
    )


def _synthesize_async_descriptor(raw_attr: Any, async_name: str) -> Any | None:
    if inspect.isfunction(raw_attr):
        if is_coroutine_callable(raw_attr):
            return None
        return _make_async_twin(raw_attr, async_name)

    if isinstance(raw_attr, staticmethod):
        inner_fn = raw_attr.__func__
        if is_coroutine_callable(inner_fn):
            return None
        return staticmethod(_make_async_twin(inner_fn, async_name))

    if isinstance(raw_attr, classmethod):
        inner_cm = raw_attr.__func__
        if is_coroutine_callable(inner_cm):
            return None
        return classmethod(_make_async_twin(inner_cm, async_name))

    return None


@overload
def auto_async[T: type](cls: T) -> T:
    pass


@overload
def auto_async(
    cls: None = None,
    *,
    suffix: str = "_async",
    exclude: Collection[str] = (),
) -> _ClassDecorator:
    pass


def auto_async(
    cls: type[Any] | None = None,
    *,
    suffix: str = "_async",
    exclude: Collection[str] = (),
) -> Any:
    """Class decorator generating thread-offloaded async method twins for public sync methods.

    Args:
        cls: Class to decorate when used as bare ``@auto_async`` without parentheses.
        suffix: Suffix appended to synthesized async method names (defaults to ``"_async"``).
        exclude: Collection of public method names to skip during async twin synthesis.

    Returns:
        Decorated class when applied directly, or class decorator callable when configured with
        keyword options.

    Raises:
        ValueError: If ``suffix`` is empty.

    Notes/Architectural Intent:
        Eliminates repetitive ``async def op_async(...)`` boilerplate when adapting synchronous
        third-party SDKs into async CQRS handlers. Inspects ``cls.__dict__`` directly so
        ``@property`` descriptors are never evaluated during decoration, preserves manually authored
        async methods without overwriting them, and delegates each wrapper factory cleanly to avoid
        loop-variable late-binding bugs.
    """
    if not suffix:
        msg = "suffix must be a non-empty string."
        raise ValueError(msg)

    excluded = frozenset(exclude)

    def _decorate[T: type](target_cls: T) -> T:
        for attr_name, raw_attr in list(target_cls.__dict__.items()):
            if attr_name.startswith("_") or attr_name in excluded:
                continue
            async_name = f"{attr_name}{suffix}"
            if hasattr(target_cls, async_name):
                continue
            twin = _synthesize_async_descriptor(raw_attr, async_name)
            if twin is not None:
                setattr(target_cls, async_name, twin)
        return target_cls

    if cls is not None:
        return _decorate(cls)

    return _decorate
