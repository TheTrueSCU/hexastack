"""Hypothesis strategy generators and testing helpers for CQRS messages and domain models.

Notes/Architectural Intent:
    Provides automated Hypothesis strategies derived from Pydantic and dataclass models
    to enable contract-driven fuzzing and invariant testing on Command/Query pipelines.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort

__all__ = [
    "cqrs_strategy",
    "flag_scope",
    "parametrize_flags",
]


def cqrs_strategy[T](model_cls: type[T], **strategy_overrides: Any) -> Any:
    """Generate a Hypothesis strategy for any Pydantic model or dataclass CQRS message.

    Args:
        model_cls: Command, Query, Event, or Generic DTO type.
        **strategy_overrides: Explicit field strategy overrides.

    Returns:
        Hypothesis search strategy generating instances of `model_cls`.

    Raises:
        MissingDependencyError: If `hypothesis` is not installed.
    """
    try:
        from hypothesis import strategies as st
    except ImportError as e:
        raise MissingDependencyError(
            "hypothesis is required for cqrs_strategy. "
            "Install with 'pip install hypothesis' or 'pip install hexastack[testing]'."
        ) from e

    # If it's a Pydantic model, hypothesis integrates via st.from_type or pydantic plugin
    try:
        return st.builds(model_cls, **strategy_overrides)
    except Exception:
        return st.from_type(model_cls)


@contextmanager
def flag_scope(
    flags_adapter: FeatureFlagPort,
    overrides: dict[str, Any],
    *,
    context: EvaluationContext | None = None,
) -> Iterator[None]:
    """Temporarily override feature flags within a context block for test isolation.

    Notes/Architectural Intent:
        Saves previous flag state and restores it on exit.
    """
    previous_state: dict[str, Any] = {}
    adapter_any: Any = flags_adapter
    for key, value in overrides.items():
        if hasattr(adapter_any, "get_raw_flag"):
            previous_state[key] = adapter_any.get_raw_flag(key, context=context)
        elif hasattr(adapter_any, "is_enabled"):
            previous_state[key] = adapter_any.is_enabled(key, context=context)

        if hasattr(adapter_any, "set_flag"):
            adapter_any.set_flag(key, value)

    try:
        yield
    finally:
        for key, prev in previous_state.items():
            if hasattr(adapter_any, "set_flag"):
                adapter_any.set_flag(key, prev)


def parametrize_flags(flag_key: str, values: list[bool] | tuple[bool, ...]) -> Any:
    """Pytest helper decorator to parametrize a test over multiple boolean flag states."""
    try:
        import pytest

        return pytest.mark.parametrize(f"flag__{flag_key.replace('.', '_')}", values)
    except ImportError as e:
        raise MissingDependencyError("pytest is required for parametrize_flags.") from e
