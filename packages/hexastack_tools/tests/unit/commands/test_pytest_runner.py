"""Unit tests for pytest runner commands."""

from hexastack_tools.commands.pytest_runner import (
    archon_generate_main,
    run_main,
)


def test_pytest_runner_callables() -> None:
    """Verify pytest runner callables."""
    assert callable(archon_generate_main)
    assert callable(run_main)
