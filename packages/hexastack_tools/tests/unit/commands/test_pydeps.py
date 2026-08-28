"""Unit tests for pydeps command."""

from hexastack_tools.commands.pydeps import generate_main


def test_pydeps_generate_main_callable() -> None:
    """Verify pydeps generate main callable."""
    assert callable(generate_main)
