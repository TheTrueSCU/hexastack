"""Unit tests for GitHub presenters across Rich, JSON, and Markdown formats.

Notes/Architectural Intent:
    Verifies that GitHubPresenterPort implementations correctly format PR summaries,
    checks, repo status, review threads, and CodeQL alerts.
"""

from __future__ import annotations

import io

from rich.console import Console

from hexastack_tools.adapters.presenters.github import (
    JsonGitHubPresenterAdapter,
    MarkdownGitHubPresenterAdapter,
    RichGitHubPresenterAdapter,
    create_github_presenter,
)
from hexastack_tools.domain.github import (
    CheckRunFinding,
    ChecksReport,
    CodeScanningReport,
    ExaminePrReport,
    PrSummary,
    RepoStatus,
    ReviewComment,
    ReviewThread,
    SecurityAlert,
    SecurityCommentsReport,
)


def _make_dummy_pr_summary(clean: bool = True) -> PrSummary:
    checks = (
        CheckRunFinding(
            "CI",
            "completed",
            "success" if clean else "failure",
            "https://actions.com/1",
        ),
    )
    threads = (
        ReviewThread(
            "thread-1", True, (ReviewComment("c1", "alice", "LGTM", "2026-09-01"),)
        ),
    )
    return PrSummary(
        number=42,
        title="Test PR",
        author="alice",
        state="open",
        mergeable="clean" if clean else "dirty",
        is_draft=False,
        head_ref="feat/branch",
        base_ref="main",
        html_url="https://github.com/org/repo/pull/42",
        check_runs=checks,
        review_threads=threads,
    )


def _make_dummy_repo_status() -> RepoStatus:
    return RepoStatus(
        name="hexastack",
        owner="TheTrueSCU",
        visibility="public",
        private=False,
        default_branch="main",
        allow_auto_merge=True,
        allow_squash_merge=True,
        has_pages=False,
        actions_enabled=True,
        allowed_actions="all",
        default_workflow_permissions="read",
        can_approve_pull_request_reviews=False,
        required_status_checks=("CI",),
    )


def test_create_github_presenter():
    """Verify factory returns appropriate presenter adapter."""
    assert isinstance(create_github_presenter("table"), RichGitHubPresenterAdapter)
    assert isinstance(create_github_presenter("rich"), RichGitHubPresenterAdapter)
    assert isinstance(create_github_presenter("json"), JsonGitHubPresenterAdapter)
    assert isinstance(
        create_github_presenter("markdown"), MarkdownGitHubPresenterAdapter
    )


def test_rich_github_presenter():
    """Verify Rich presenter executes without error."""
    out = io.StringIO()
    console = Console(file=out, color_system=None, width=120)
    presenter = RichGitHubPresenterAdapter(console=console)

    clean_report = ExaminePrReport(summary=_make_dummy_pr_summary(clean=True))
    assert presenter.present_pr_summary(clean_report) == 0

    dirty_report = ExaminePrReport(summary=_make_dummy_pr_summary(clean=False))
    assert presenter.present_pr_summary(dirty_report) == 1

    checks_report = ChecksReport("main", clean_report.summary.check_runs)
    assert presenter.present_checks(checks_report) == 0

    assert presenter.present_repo_status(_make_dummy_repo_status()) == 0

    sec_report = SecurityCommentsReport(42, clean_report.summary.review_threads)
    assert presenter.present_security_comments(sec_report) == 0

    # Code scanning - multiple alerts
    alert = SecurityAlert(
        1,
        "py/injection",
        "Command injection",
        "high",
        "critical",
        "open",
        "src/foo.py",
        1,
        2,
        "Dangerous exec",
    )
    scan_report = CodeScanningReport(alerts=(alert,), state="open")
    assert presenter.present_code_scanning(scan_report) == 0

    # Code scanning - single alert
    single_scan_report = CodeScanningReport(single_alert=alert, state="open")
    assert presenter.present_code_scanning(single_scan_report) == 0


def test_json_github_presenter():
    """Verify JSON presenter generates valid JSON."""
    out = io.StringIO()
    console = Console(file=out, color_system=None)
    presenter = JsonGitHubPresenterAdapter(console=console)

    clean_report = ExaminePrReport(summary=_make_dummy_pr_summary(clean=True))
    assert presenter.present_pr_summary(clean_report) == 0

    checks_report = ChecksReport("main", clean_report.summary.check_runs)
    assert presenter.present_checks(checks_report) == 0

    assert presenter.present_repo_status(_make_dummy_repo_status()) == 0

    sec_report = SecurityCommentsReport(42, clean_report.summary.review_threads)
    assert presenter.present_security_comments(sec_report) == 0

    alert = SecurityAlert(
        1,
        "py/injection",
        "Command injection",
        "high",
        "critical",
        "open",
        "src/foo.py",
        1,
        2,
        "Dangerous exec",
    )
    scan_report = CodeScanningReport(alerts=(alert,), single_alert=alert, state="open")
    assert presenter.present_code_scanning(scan_report) == 0


def test_markdown_github_presenter():
    """Verify Markdown presenter outputs markdown tables."""
    out = io.StringIO()
    console = Console(file=out, color_system=None)
    presenter = MarkdownGitHubPresenterAdapter(console=console)

    clean_report = ExaminePrReport(summary=_make_dummy_pr_summary(clean=True))
    assert presenter.present_pr_summary(clean_report) == 0

    checks_report = ChecksReport("main", clean_report.summary.check_runs)
    assert presenter.present_checks(checks_report) == 0

    assert presenter.present_repo_status(_make_dummy_repo_status()) == 0

    sec_report = SecurityCommentsReport(42, clean_report.summary.review_threads)
    assert presenter.present_security_comments(sec_report) == 0

    alert = SecurityAlert(
        1,
        "py/injection",
        "Command injection",
        "high",
        "critical",
        "open",
        "src/foo.py",
        1,
        2,
        "Dangerous exec",
    )
    scan_report = CodeScanningReport(alerts=(alert,), state="open")
    assert presenter.present_code_scanning(scan_report) == 0

    single_scan_report = CodeScanningReport(single_alert=alert, state="open")
    assert presenter.present_code_scanning(single_scan_report) == 0
