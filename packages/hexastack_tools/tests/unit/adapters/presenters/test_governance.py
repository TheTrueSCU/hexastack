"""Unit tests for RichGovernancePresenterAdapter.

Notes/Architectural Intent:
    Verifies that RichGovernancePresenterAdapter properly renders success
    dashboards, failure summaries, and detailed error panels to the console.
"""

from io import StringIO

from rich.console import Console

from hexastack_tools.adapters.presenters.governance import (
    RichGovernancePresenterAdapter,
)
from hexastack_tools.domain.governance import (
    CheckResult,
    CheckStatus,
    SanityCheckReport,
)


def test_present_sanity_dashboard_success():
    """Verify rendering of completely successful sanity report."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = RichGovernancePresenterAdapter(console=console)

    res1 = CheckResult("Ruff", "core", CheckStatus.PASS, 0.05, "Clean")
    res2 = CheckResult("Ty", "core", CheckStatus.PASS, 0.12, "Types valid")
    report = SanityCheckReport(results=(res1, res2), total_duration=0.17, exit_code=0)

    exit_code = presenter.present_sanity_dashboard(report)
    assert exit_code == 0
    output = buf.getvalue()
    assert "Hexastack Scoped Sanity Check Dashboard" in output
    assert "All 2 sanity checks passed" in output


def test_present_sanity_dashboard_failure_with_error_panel():
    """Verify rendering of failing checks and diagnostic error panels."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = RichGovernancePresenterAdapter(console=console)

    res_fail = CheckResult(
        check_name="Complexipy",
        target_name="cqrs",
        status=CheckStatus.FAIL,
        duration=0.25,
        details="1 function exceeds 25",
        error_output="src/pkg.py heavy_fn (score: 30 > 25)",
    )
    report = SanityCheckReport(results=(res_fail,), total_duration=0.25, exit_code=1)

    exit_code = presenter.present_sanity_dashboard(report)
    assert exit_code == 1
    output = buf.getvalue()
    assert "1 check(s) failed" in output
    assert "heavy_fn" in output
