"""Unit tests for CLI help extractor utilities."""

from hexastack_tools.utils.help_extractor import (
    clean_help_output,
    extract_command_help,
    extract_subcommands_from_help,
)


def test_clean_help_output() -> None:
    """Ensure clean_help_output strips ANSI and trims trailing spaces."""
    raw = "\x1b[31mUsage: test [OPTIONS]\x1b[0m   \nSome text   "
    cleaned = clean_help_output(raw)
    assert cleaned == "Usage: test [OPTIONS]\nSome text"


def test_extract_subcommands_from_help() -> None:
    """Ensure subcommands are extracted correctly from help tables."""
    help_text = """
╭─ Commands ────────────────────────────────────────╮
│ info     Display installed packages.              │
│ doctor   Run system diagnostics.                  │
╰───────────────────────────────────────────────────╯
"""
    subs = extract_subcommands_from_help(help_text)
    assert subs == ["info", "doctor"]


def test_extract_command_help_nonexistent() -> None:
    """Ensure nonexistent command returns error string without crashing."""
    err = extract_command_help(["nonexistent-tool-xyz-123"])
    assert "Error extracting help" in err or "nonexistent-tool-xyz-123" in err
