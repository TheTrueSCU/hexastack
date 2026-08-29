"""Unit tests for checks presenter."""

from hexastack_tools.adapters.presenters.checks import (
    build_checks_table,
    present_checks,
    render_checks_json,
    render_checks_plain,
)
from hexastack_tools.domain.github import CheckRunFinding, OutputFormat


def test_checks_presenter_formats() -> None:
    """Verify rich, json, and plain presentation for checks."""
    check = CheckRunFinding(
        name="pytest",
        status="completed",
        conclusion="success",
        details_url="https://ci.example.com/1",
        workflow_name="CI",
    )
    checks = [check]

    table = build_checks_table(checks, "main")
    assert table.title is not None

    json_out = render_checks_json(checks, "main")
    assert '"total_checks": 1' in json_out
    assert '"pytest"' in json_out

    plain_out = render_checks_plain(checks, "main")
    assert "REF\tmain\t1" in plain_out
    assert "CHECK\tCI\tpytest\tcompleted\tsuccess" in plain_out

    present_checks(checks, "main", OutputFormat.RICH)
    present_checks(checks, "main", OutputFormat.JSON)
    present_checks(checks, "main", OutputFormat.PLAIN)
