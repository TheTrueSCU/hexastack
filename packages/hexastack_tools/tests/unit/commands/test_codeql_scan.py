"""Unit tests for codeql_scan command."""

from hexastack_tools.commands.codeql_scan import main


def test_codeql_scan_main_callable() -> None:
    """Verify codeql scanner main callable."""
    assert callable(main)
