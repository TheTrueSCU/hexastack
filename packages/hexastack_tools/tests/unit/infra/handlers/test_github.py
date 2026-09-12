"""Unit tests for GitHub command handlers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from hexastack_tools.domain.github import (
    CheckRunFinding,
    ChecksReport,
    CodeScanningReport,
    ExaminePrCommand,
    ExaminePrReport,
    InspectChecksCommand,
    InspectCodeScanningCommand,
    InspectRepoCommand,
    InspectSecurityCommentsCommand,
    PrSummary,
    RepoStatus,
    ReviewThread,
    SecurityAlert,
    SecurityCommentsReport,
)
from hexastack_tools.infra.handlers.github import (
    ExaminePrHandler,
    InspectChecksHandler,
    InspectCodeScanningHandler,
    InspectRepoHandler,
    InspectSecurityCommentsHandler,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock GitHubApiPort client."""
    return MagicMock()


def test_examine_pr_handler_explicit_pr(mock_client: MagicMock) -> None:
    """Test ExaminePrHandler with explicit PR number."""
    finding = CheckRunFinding(
        name="pytest",
        status="completed",
        conclusion="failure",
        details_url="https://github.com/TheTrueSCU/hexastack/actions/runs/12345/job/67890",
    )
    summary = PrSummary(
        number=42,
        title="Fix bug",
        author="alice",
        state="open",
        mergeable="mergeable",
        is_draft=False,
        head_ref="fix",
        base_ref="main",
        html_url="https://github.com/TheTrueSCU/hexastack/pull/42",
        check_runs=(finding,),
    )
    mock_client.get_pr_summary.return_value = summary
    mock_client.get_failed_run_logs.return_value = "FAILED test_something"

    handler = ExaminePrHandler(mock_client)
    cmd = ExaminePrCommand(pr_number=42, show_details=True)
    report = handler.handle(cmd)

    assert isinstance(report, ExaminePrReport)
    assert report.summary.number == 42
    assert report.show_details is True
    assert report.failed_logs == {"pytest": "FAILED test_something"}
    mock_client.get_pr_summary.assert_called_once_with(42)
    mock_client.get_failed_run_logs.assert_called_once_with("12345")


def test_examine_pr_handler_auto_discovery(mock_client: MagicMock) -> None:
    """Test ExaminePrHandler auto-discovering current branch PR number."""
    summary = PrSummary(
        number=99,
        title="Auto PR",
        author="bob",
        state="open",
        mergeable="mergeable",
        is_draft=False,
        head_ref="feature",
        base_ref="main",
        html_url="https://github.com/TheTrueSCU/hexastack/pull/99",
    )
    mock_client.get_pr_summary.return_value = summary

    handler = ExaminePrHandler(mock_client)
    cmd = ExaminePrCommand(pr_number=None)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=json.dumps({"number": 99}))
        report = handler.handle(cmd)

    assert report.summary.number == 99
    assert report.failed_logs is None
    mock_client.get_pr_summary.assert_called_once_with(99)


def test_examine_pr_handler_auto_discovery_failures(mock_client: MagicMock) -> None:
    """Test ExaminePrHandler auto-discovery error handling."""
    handler = ExaminePrHandler(mock_client)
    cmd = ExaminePrCommand(pr_number=None)

    with (
        patch("subprocess.run", side_effect=RuntimeError("no gh")),
        pytest.raises(RuntimeError, match="Could not auto-discover PR"),
    ):
        handler.handle(cmd)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=json.dumps({"other": 1}))
        with pytest.raises(RuntimeError, match="Could not determine PR number"):
            handler.handle(cmd)


def test_examine_pr_handler_log_edge_cases(mock_client: MagicMock) -> None:
    """Test ExaminePrHandler log fetching edge cases."""
    findings = (
        CheckRunFinding(name="pass", status="completed", conclusion="success"),
        CheckRunFinding(
            name="external_fail",
            status="completed",
            conclusion="failure",
            details_url="https://external-ci.com/run/1",
        ),
        CheckRunFinding(
            name="malformed_run",
            status="completed",
            conclusion="failure",
            details_url="https://github.com/TheTrueSCU/hexastack/actions/runs/",
        ),
    )
    summary = PrSummary(
        number=10,
        title="Edge cases",
        author="carol",
        state="open",
        mergeable="mergeable",
        is_draft=False,
        head_ref="edge",
        base_ref="main",
        html_url="https://github.com/TheTrueSCU/hexastack/pull/10",
        check_runs=findings,
    )
    mock_client.get_pr_summary.return_value = summary

    handler = ExaminePrHandler(mock_client)
    report = handler.handle(ExaminePrCommand(pr_number=10))

    assert report.failed_logs is None


def test_inspect_checks_handler_pr_number(mock_client: MagicMock) -> None:
    """Test InspectChecksHandler with numeric PR number."""
    finding = CheckRunFinding(name="lint", status="completed", conclusion="success")
    summary = PrSummary(
        number=55,
        title="Check PR",
        author="dan",
        state="open",
        mergeable="mergeable",
        is_draft=False,
        head_ref="ref",
        base_ref="main",
        html_url="url",
        check_runs=(finding,),
    )
    mock_client.get_pr_summary.return_value = summary

    handler = InspectChecksHandler(mock_client)
    report = handler.handle(InspectChecksCommand(ref_or_pr="55"))

    assert isinstance(report, ChecksReport)
    assert report.ref_or_pr == "55"
    assert len(report.check_runs) == 1
    assert report.has_failure is False
    mock_client.get_pr_summary.assert_called_once_with(55)


def test_inspect_checks_handler_git_ref(mock_client: MagicMock) -> None:
    """Test InspectChecksHandler with git ref string."""
    finding = CheckRunFinding(
        name="typecheck", status="completed", conclusion="failure"
    )
    mock_client.get_check_runs.return_value = [finding]

    handler = InspectChecksHandler(mock_client)
    report = handler.handle(InspectChecksCommand(ref_or_pr="feature-branch"))

    assert report.ref_or_pr == "feature-branch"
    assert report.has_failure is True
    mock_client.get_check_runs.assert_called_once_with("feature-branch")


def test_inspect_code_scanning_single_alert(mock_client: MagicMock) -> None:
    """Test InspectCodeScanningHandler with single alert inspection."""
    alert = SecurityAlert(
        number=101,
        rule_id="py/command-injection",
        rule_description="Command injection vulnerability",
        severity="critical",
        security_severity_level="9.8",
        state="open",
        path="src/app.py",
        start_line=10,
        end_line=12,
        message="Unescaped input",
    )
    mock_client.get_single_alert.return_value = alert

    handler = InspectCodeScanningHandler(mock_client)
    report = handler.handle(InspectCodeScanningCommand(alert_number=101))

    assert isinstance(report, CodeScanningReport)
    assert report.single_alert == alert
    assert report.alerts == (alert,)
    mock_client.get_single_alert.assert_called_once_with(101)


def test_inspect_code_scanning_filter_alerts(mock_client: MagicMock) -> None:
    """Test InspectCodeScanningHandler filtering by rule, package, and severity."""
    alert1 = SecurityAlert(
        number=1,
        rule_id="py/sql-injection",
        rule_description="SQL injection",
        severity="error",
        security_severity_level="high",
        state="open",
        path="packages/hexastack_db/src/repo.py",
        start_line=5,
        end_line=6,
        message="Bad SQL",
    )
    alert2 = SecurityAlert(
        number=2,
        rule_id="py/unused-import",
        rule_description="Unused import",
        severity="warning",
        security_severity_level="low",
        state="open",
        path="packages/hexastack_core/src/model.py",
        start_line=1,
        end_line=1,
        message="Unused",
    )
    mock_client.get_code_scanning_alerts.return_value = [alert1, alert2]

    handler = InspectCodeScanningHandler(mock_client)

    # Filter by rule
    rep1 = handler.handle(InspectCodeScanningCommand(rule_filter="sql"))
    assert len(rep1.alerts) == 1
    assert rep1.alerts[0].number == 1

    # Filter by severity
    rep2 = handler.handle(InspectCodeScanningCommand(severity_filter="warning"))
    assert len(rep2.alerts) == 1
    assert rep2.alerts[0].number == 2

    # Filter by package
    rep3 = handler.handle(InspectCodeScanningCommand(package_filter="hexastack_db"))
    assert len(rep3.alerts) == 1
    assert rep3.alerts[0].number == 1

    # No filter
    rep4 = handler.handle(InspectCodeScanningCommand())
    assert len(rep4.alerts) == 2


def test_inspect_repo_handler(mock_client: MagicMock) -> None:
    """Test InspectRepoHandler parsing owner and target repository."""
    status = RepoStatus(
        name="hexastack",
        owner="TheTrueSCU",
        visibility="public",
        private=False,
        default_branch="main",
        allow_auto_merge=True,
        allow_squash_merge=True,
        has_pages=True,
        actions_enabled=True,
        allowed_actions="all",
        default_workflow_permissions="read",
        can_approve_pull_request_reviews=False,
    )
    mock_client.get_repo_status.return_value = status

    handler = InspectRepoHandler(mock_client)

    # With owner/repo
    rep1 = handler.handle(InspectRepoCommand(repo_name="TheTrueSCU/hexastack"))
    assert rep1 == status
    mock_client.get_repo_status.assert_called_with(owner="TheTrueSCU", repo="hexastack")

    # With repo only
    rep2 = handler.handle(InspectRepoCommand(repo_name="my-repo"))
    assert rep2 == status
    mock_client.get_repo_status.assert_called_with(owner=None, repo="my-repo")

    # With None
    rep3 = handler.handle(InspectRepoCommand(repo_name=None))
    assert rep3 == status
    mock_client.get_repo_status.assert_called_with(owner=None, repo=None)


def test_inspect_security_comments_handler(mock_client: MagicMock) -> None:
    """Test InspectSecurityCommentsHandler."""
    thread = ReviewThread(id="thread-1", is_resolved=False)
    summary = PrSummary(
        number=77,
        title="Security PR",
        author="eve",
        state="open",
        mergeable="mergeable",
        is_draft=False,
        head_ref="sec",
        base_ref="main",
        html_url="url",
        review_threads=(thread,),
    )
    mock_client.get_pr_summary.return_value = summary

    handler = InspectSecurityCommentsHandler(mock_client)
    report = handler.handle(InspectSecurityCommentsCommand(pr_number=77))

    assert isinstance(report, SecurityCommentsReport)
    assert report.pr_number == 77
    assert len(report.threads) == 1
    assert report.threads[0].id == "thread-1"
    mock_client.get_pr_summary.assert_called_once_with(77)
