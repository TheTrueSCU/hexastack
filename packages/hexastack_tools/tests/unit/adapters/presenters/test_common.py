"""Unit tests for common presenter utilities."""

import sys
from unittest.mock import patch

from hexastack_tools.adapters.presenters.common import resolve_output_format
from hexastack_tools.domain.github import OutputFormat


def test_resolve_output_format_explicit() -> None:
    """Verify explicit formats are preserved as-is."""
    assert resolve_output_format(OutputFormat.RICH) == OutputFormat.RICH
    assert resolve_output_format(OutputFormat.JSON) == OutputFormat.JSON
    assert resolve_output_format(OutputFormat.PLAIN) == OutputFormat.PLAIN


def test_resolve_output_format_auto_piped() -> None:
    """Verify auto-detection resolves to PLAIN when stdout is not a TTY (piped)."""
    with patch.object(sys.stdout, "isatty", return_value=False):
        assert resolve_output_format(OutputFormat.AUTO) == OutputFormat.PLAIN


def test_resolve_output_format_auto_terminal() -> None:
    """Verify auto-detection resolves to RICH when stdout is a TTY."""
    with patch.object(sys.stdout, "isatty", return_value=True):
        assert resolve_output_format(OutputFormat.AUTO) == OutputFormat.RICH
