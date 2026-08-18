from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ClearableRegistry(Protocol):
    """Protocol for registries that support resetting state."""

    def clear(self) -> None:
        """Clear all registered items in the registry."""
        ...


__all__ = [
    "ClearableRegistry",
    "isolate_registries",
]


@contextmanager
def isolate_registries(*registries: Any) -> Iterator[None]:
    """Context manager ensuring registry state is isolated during execution.

    Notes/Architectural Intent:
        Calls .clear() on all supplied registries both before entering and upon exiting
        the context block, preventing test cross-contamination in shared registries.

    Args:
        *registries: Clearable registry instances.

    Yields:
        None.
    """
    for reg in registries:
        if hasattr(reg, "clear") and callable(reg.clear):
            reg.clear()
    try:
        yield
    finally:
        for reg in registries:
            if hasattr(reg, "clear") and callable(reg.clear):
                reg.clear()
