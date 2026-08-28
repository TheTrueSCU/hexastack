"""Unit tests for inline_snapshot command."""

from hexastack_tools.commands.inline_snapshot import main


def test_inline_snapshot_main_callable() -> None:
    """Verify inline snapshot main callable."""
    assert callable(main)
