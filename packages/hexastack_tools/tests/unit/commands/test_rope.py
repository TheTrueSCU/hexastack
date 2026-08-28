"""Unit tests for rope commands."""

from hexastack_tools.commands.rope import (
    alphabetize_main,
    run_main,
)


def test_rope_callables() -> None:
    """Verify rope callables."""
    assert callable(alphabetize_main)
    assert callable(run_main)
