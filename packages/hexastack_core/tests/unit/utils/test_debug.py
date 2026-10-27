"""Unit tests for snoop execution tracing and debugging utilities.

Notes/Architectural Intent:
    Verifies that get_snoop_tracer and snoop_tracer operate seamlessly as decorators
    and context managers when snoop is present, and gracefully degrade to zero-overhead
    no-ops when snoop is absent.
"""

import sys

import pytest

from hexastack_core.utils.debug import (
    get_snoop_tracer,
    is_snoop_available,
    snoop_tracer,
)


def test_is_snoop_available_installed() -> None:
    """Verify is_snoop_available reports True when snoop is installed."""
    available = is_snoop_available()
    assert available is True


def test_snoop_tracer_active_decorator_bare() -> None:
    """Verify snoop_tracer operates as a bare decorator on a function."""

    @snoop_tracer
    def multiply(x: int, y: int) -> int:
        return x * y

    result = multiply(4, 5)
    assert result == 20


def test_snoop_tracer_active_decorator_with_args() -> None:
    """Verify snoop_tracer operates as a parameterized decorator."""

    @snoop_tracer(depth=1)
    def compute(val: int) -> int:
        return val + 10

    result = compute(7)
    assert result == 17


def test_snoop_tracer_active_context_manager() -> None:
    """Verify snoop_tracer operates as a context manager."""
    total = 0
    with snoop_tracer():
        total = 10 + 20

    assert total == 30


def test_snoop_tracer_fallback_when_uninstalled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify snoop_tracer degrades to zero-overhead no-op when snoop is missing."""
    monkeypatch.setitem(sys.modules, "snoop", None)

    available = is_snoop_available()
    assert available is False

    # 1. Bare decorator fallback
    @get_snoop_tracer
    def fallback_bare(a: int) -> int:
        return a * 3

    res_bare = fallback_bare(10)
    assert res_bare == 30

    # 2. Parameterized decorator fallback
    @get_snoop_tracer(depth=2, watch=("a",))
    def fallback_params(a: int) -> int:
        return a + 5

    res_params = fallback_params(15)
    assert res_params == 20

    # 3. Context manager fallback
    val = 0
    with get_snoop_tracer():
        val = 99

    assert val == 99
