"""Unit tests for test_parity command."""

from hexastack_tools.commands.test_parity import main


def test_test_parity_main_callable() -> None:
    """Verify test parity main callable."""
    assert callable(main)
