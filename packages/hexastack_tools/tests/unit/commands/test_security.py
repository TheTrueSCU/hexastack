"""Unit tests for security command."""

from hexastack_tools.commands.security import main


def test_security_main_callable() -> None:
    """Verify security command main callable."""
    assert callable(main)
