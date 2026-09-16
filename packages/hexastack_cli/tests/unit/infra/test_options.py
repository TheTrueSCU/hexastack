"""Unit tests for CLI options factories and formatting resolvers."""

from __future__ import annotations

from unittest.mock import patch

from hexastack_cli.domain.options import OutputFormat
from hexastack_cli.infra.options import format_option, resolve_format


def test_resolve_format_explicit() -> None:
    """Explicit formats should be normalized and returned directly."""
    res_table = resolve_format("TABLE")
    assert res_table == "table"

    res_enum = resolve_format(OutputFormat.JSON)
    assert res_enum == "json"


def test_resolve_format_auto_tty() -> None:
    """Auto format when connected to TTY should return default_tty."""
    with patch("sys.stdout.isatty", return_value=True):
        res = resolve_format(OutputFormat.AUTO, default_tty="rich", default_pipe="json")
        assert res == "rich"


def test_resolve_format_auto_pipe() -> None:
    """Auto format when piped (not TTY) should return default_pipe."""
    with patch("sys.stdout.isatty", return_value=False):
        res = resolve_format("auto", default_tty="rich", default_pipe="json")
        assert res == "json"


def test_format_option_creation() -> None:
    """format_option should return a valid Typer Option with default flag."""
    opt = format_option(default="json")
    default_val = opt.default
    assert default_val == "json"
