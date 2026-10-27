"""Hermetic clock manipulation and time-travel utilities for tests.

Notes/Architectural Intent:
    Provides high-performance, deterministic clock mocking powered by `time-machine`.
    Replaces brittle `time.sleep` calls and monkey-patched `datetime.now()` with C-level
    clock interception, guaranteeing leak-free test isolation across parallel pytest-xdist workers.
"""

from typing import Any

from hexastack_core.utils.imports import require_dependency

__all__ = [
    "freeze_time",
]


def freeze_time(destination: Any = 0.0, tick: bool = False) -> Any:
    """Freeze or travel to a specific point in time across sync and async contexts.

    Notes/Architectural Intent:
        Delegates to `time_machine.travel`, intercepting `time.time()`, `time.monotonic()`,
        and `datetime.datetime.now()` at the C level without event loop drift.
        Supports usage as a synchronous context manager (`with freeze_time(...):`),
        asynchronous context manager (`async with freeze_time(...):`), or test decorator (`@freeze_time(...)`).

    Args:
        destination: Target epoch timestamp (float/int), datetime, or timedelta offset.
        tick: Whether clock continues to tick from destination point (default: False).

    Returns:
        Time-machine traveller context manager / decorator object.

    Raises:
        MissingDependencyError: If `time-machine` is not installed.
    """
    time_machine = require_dependency(
        "time_machine",
        extra="testing",
        package="hexastack-core",
        feature_name="freeze_time",
    )
    return time_machine.travel(destination, tick=tick)
