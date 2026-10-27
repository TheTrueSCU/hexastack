"""Algorithmic tracing and execution debugging utilities powered by snoop.

Notes/Architectural Intent:
    Provides a zero-overhead, production-safe tracing decorator and context manager.
    When `snoop` is installed and debugging is active, it delivers line-by-line
    variable mutation tracking and function execution flow diagnostics.
    If `snoop` is absent or tracing is inactive, it gracefully degrades to a zero-cost no-op,
    guaranteeing that test harnesses, domain algorithms, and production servers remain uninhibited.
"""

from collections.abc import Callable
from typing import Any

from hexastack_core.utils.imports import optional_dependency

__all__ = [
    "get_snoop_tracer",
    "is_snoop_available",
    "snoop_tracer",
]


class _NoOpTracer:
    """Zero-overhead fallback when snoop is not installed or disabled."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]

        def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return _decorator

    def __enter__(self) -> "_NoOpTracer":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


def is_snoop_available() -> bool:
    """Check if the snoop debugging package is installed and importable.

    Notes/Architectural Intent:
        Used by DevTools and diagnostic endpoints to verify whether algorithmic
        tracing capabilities are enabled in the current environment.

    Returns:
        True if snoop is available, False otherwise.

    Raises:
        None.
    """
    snoop_mod = optional_dependency("snoop")
    return snoop_mod is not None


def get_snoop_tracer(*args: Any, **kwargs: Any) -> Any:
    """Obtain a snoop execution tracer or zero-overhead fallback.

    Notes/Architectural Intent:
        Wraps `snoop.snoop(*args, **kwargs)` if snoop is installed.
        Returns a no-op callable / context manager if snoop is missing.

    Args:
        *args: Positional arguments forwarded to snoop (e.g. target function or watch targets).
        **kwargs: Keyword arguments forwarded to snoop (e.g. watch, depth, prefix).

    Returns:
        Configured snoop tracer or _NoOpTracer instance.

    Raises:
        None.
    """
    snoop_mod = optional_dependency("snoop")
    if snoop_mod is None:
        tracer = _NoOpTracer()
        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return tracer(args[0])
        return tracer

    return snoop_mod.snoop(*args, **kwargs)


# Module-level convenience tracer
snoop_tracer = get_snoop_tracer
