"""Unit tests for pr_examine command."""

from hexastack_tools.commands.pr_examine import main


def test_pr_examine_main_callable() -> None:
    """Verify pr examine main callable."""
    assert callable(main)
