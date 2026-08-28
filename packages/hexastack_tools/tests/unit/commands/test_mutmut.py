"""Unit tests for mutmut commands."""

from hexastack_tools.commands.mutmut import (
    inspect_main,
    run_main,
)


def test_mutmut_callables() -> None:
    """Verify mutmut callables."""
    assert callable(inspect_main)
    assert callable(run_main)
