"""Unit tests for OutputFormat domain enumeration."""

from __future__ import annotations

from hexastack_cli.domain.options import OutputFormat


def test_output_format_members() -> None:
    """Verify OutputFormat defines all standard presentation formats."""
    expected = {"auto", "json", "markdown", "plain", "rich", "table"}
    values = {f.value for f in OutputFormat}
    assert values == expected


def test_output_format_str_conversion() -> None:
    """Verify OutputFormat members serialize cleanly as lowercase strings."""
    auto_val = str(OutputFormat.AUTO)
    assert auto_val == "auto"

    json_val = OutputFormat.JSON.value
    assert json_val == "json"
