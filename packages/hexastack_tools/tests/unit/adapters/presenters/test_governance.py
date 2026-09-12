"""Unit tests for multi-format governance presenters.

Notes/Architectural Intent:
    Verifies that Rich, JSON, and Markdown governance presenters properly
    format sanity check dashboards, __all__ statements, and test parity reports.
"""

from __future__ import annotations

import json
from io import StringIO

import pytest
from rich.console import Console

from hexastack_tools.adapters.presenters.governance import (
    JsonGovernancePresenterAdapter,
    MarkdownGovernancePresenterAdapter,
    RichGovernancePresenterAdapter,
    create_governance_presenter,
)
from hexastack_tools.domain.governance import (
    CheckResult,
    CheckStatus,
    SanityCheckReport,
)


def test_present_sanity_dashboard_rich_success():
    """Verify rendering of completely successful sanity report with Rich."""
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


def test_present_sanity_dashboard_rich_failure():
    """Verify rendering of failing checks and diagnostic error panels in Rich."""
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


def test_rich_presenter_all_statements_and_parity():
    """Verify Rich presenter handles __all__ and parity outcomes."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = RichGovernancePresenterAdapter(console=console)

    # __all__ modified count
    code_fix = presenter.present_all_statements([], modified_count=3)
    assert code_fix == 0
    assert "Formatted and alphabetized" in buf.getvalue()

    # __all__ errors
    buf.truncate(0)
    buf.seek(0)
    code_err = presenter.present_all_statements(["err: missing symbol"])
    assert code_err == 1
    out_all = buf.getvalue()
    assert "API Surface" in out_all
    assert "Integrity Violations" in out_all

    # Test parity clean
    buf.truncate(0)
    buf.seek(0)
    code_clean = presenter.present_test_parity([], [])
    assert code_clean == 0
    assert "All source modules mirror unit tests" in buf.getvalue()

    # Test parity errors
    buf.truncate(0)
    buf.seek(0)
    code_par_err = presenter.present_test_parity(
        ["missing __init__.py"], ["missing test"]
    )
    assert code_par_err == 1
    out_par = buf.getvalue()
    assert "Test Parity" in out_par


def test_json_presenter_all_methods():
    """Verify JsonGovernancePresenterAdapter serializes valid JSON for all methods."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = JsonGovernancePresenterAdapter(console=console)

    res = CheckResult("Ruff", "core", CheckStatus.PASS, 0.05, "Clean")
    report = SanityCheckReport(results=(res,), total_duration=0.05, exit_code=0)

    # 1. Sanity report
    exit_code = presenter.present_sanity_dashboard(report)
    assert exit_code == 0
    data = json.loads(buf.getvalue())
    assert data["status"] == "PASS"
    assert data["results"][0]["check"] == "Ruff"

    # 2. All statements
    buf.truncate(0)
    buf.seek(0)
    code_all = presenter.present_all_statements(["err1"], modified_count=None)
    assert code_all == 1
    data_all = json.loads(buf.getvalue())
    assert data_all["status"] == "FAIL"
    assert "err1" in data_all["errors"]

    # 3. Test parity
    buf.truncate(0)
    buf.seek(0)
    code_par = presenter.present_test_parity([], [])
    assert code_par == 0
    data_par = json.loads(buf.getvalue())
    assert data_par["status"] == "PASS"


def test_markdown_presenter_all_methods():
    """Verify MarkdownGovernancePresenterAdapter renders GitHub markdown."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    presenter = MarkdownGovernancePresenterAdapter(console=console)

    res_pass = CheckResult("Ruff", "core", CheckStatus.PASS, 0.05, "Clean")
    res_fail = CheckResult(
        "Ty", "core", CheckStatus.FAIL, 0.1, "Error", error_output="line 1: type error"
    )
    report = SanityCheckReport(
        results=(res_pass, res_fail), total_duration=0.15, exit_code=1
    )

    exit_code = presenter.present_sanity_dashboard(report)
    assert exit_code == 1
    output = buf.getvalue()
    assert "| Check | Target | Status |" in output
    assert "✅ PASS" in output
    assert "❌ FAIL" in output
    assert "<details><summary>" in output
    assert "line 1: type error" in output

    # All statements
    buf.truncate(0)
    buf.seek(0)
    code_all = presenter.present_all_statements(["err: bad sort"])
    assert code_all == 1
    assert "Integrity Violations" in buf.getvalue()

    # Parity
    buf.truncate(0)
    buf.seek(0)
    code_par = presenter.present_test_parity(["missing init"], ["missing test"])
    assert code_par == 1
    assert "| Violation Type | Details |" in buf.getvalue()


def test_create_governance_presenter_factory():
    """Verify create_governance_presenter creates correct instances and handles errors."""
    assert isinstance(
        create_governance_presenter("table"), RichGovernancePresenterAdapter
    )
    assert isinstance(
        create_governance_presenter("json"), JsonGovernancePresenterAdapter
    )
    assert isinstance(
        create_governance_presenter("markdown"), MarkdownGovernancePresenterAdapter
    )
    assert isinstance(
        create_governance_presenter("md"), MarkdownGovernancePresenterAdapter
    )

    with pytest.raises(ValueError, match="Unsupported presenter format"):
        create_governance_presenter("unknown_format")
