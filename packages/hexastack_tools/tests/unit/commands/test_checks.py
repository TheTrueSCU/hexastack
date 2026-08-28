"""Unit tests for checks command."""

from hexastack_tools.adapters.presenters.checks import build_checks_table
from hexastack_tools.commands.checks import app, checks, main
from hexastack_tools.domain.github import CheckRunFinding


def test_format_checks_table() -> None:
    """Verify checks table format output."""
    check = CheckRunFinding(
        name="unit-tests",
        status="completed",
        conclusion="success",
        details_url="https://ci.example.com",
    )
    table = build_checks_table([check], "main")
    assert table.title is not None


def test_checks_command_callables() -> None:
    """Verify checks Typer app and callables."""
    assert callable(main)
    assert callable(checks)
    assert app is not None
