"""Unit tests for checks command."""

from hexastack_tools.commands.checks import (
    format_checks_table,
)
from hexastack_tools.domain.github import CheckRunFinding


def test_format_checks_table() -> None:
    """Verify checks table rendering."""
    check = CheckRunFinding(
        name="Unit Tests",
        status="completed",
        conclusion="success",
        details_url="https://ci.example.com",
        workflow_name="CI",
    )
    table = format_checks_table([check], "test-ref")
    assert table.title is not None
    assert "test-ref" in str(table.title)
