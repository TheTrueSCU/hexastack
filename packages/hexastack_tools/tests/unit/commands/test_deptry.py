"""Unit tests for deptry command."""

from hexastack_tools.commands.deptry import main


def test_deptry_main_callable() -> None:
    """Verify deptry main callable."""
    assert callable(main)
