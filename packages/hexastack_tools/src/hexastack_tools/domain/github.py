"""Domain models and CQRS commands for GitHub inspection and verification.

Notes/Architectural Intent:
    Encapsulates GitHub API data structures, check run findings, PR summaries,
    and CQRS commands without external HTTP or presenter dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hexastack_core.domain.command import Command


class OutputFormat(StrEnum):
    """Output presentation formats supported across CLI tools."""

    AUTO = "auto"
    RICH = "rich"
    JSON = "json"
    PLAIN = "plain"


class AlertSeverity(StrEnum):
    """Normalized security and quality alert severity."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NOTE = "note"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CheckRunFinding:
    """A discrete CI check run or status check."""

    name: str
    status: str
    conclusion: str
    details_url: str = ""
    workflow_name: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


@dataclass(frozen=True)
class ReviewComment:
    """Review comment on a PR diff or discussion thread."""

    id: str | int
    author: str
    body: str
    created_at: str
    path: str | None = None
    line: int | None = None
    url: str | None = None
    diff_hunk: str | None = None
    is_review_comment: bool = False


@dataclass(frozen=True)
class ReviewThread:
    """Review discussion thread on a pull request."""

    id: str
    is_resolved: bool
    comments: tuple[ReviewComment, ...] = ()
    resolved_by: str | None = None


@dataclass(frozen=True)
class SecurityAlert:
    """GitHub code scanning or CodeQL alert."""

    number: int
    rule_id: str
    rule_description: str
    severity: str
    security_severity_level: str | None
    state: str
    path: str
    start_line: int
    end_line: int
    message: str
    help_markdown: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class PrSummary:
    """Comprehensive summary of a GitHub Pull Request."""

    number: int
    title: str
    author: str
    state: str
    mergeable: str
    is_draft: bool
    head_ref: str
    base_ref: str
    html_url: str
    check_runs: tuple[CheckRunFinding, ...] = ()
    review_threads: tuple[ReviewThread, ...] = ()
    security_alerts: tuple[SecurityAlert, ...] = ()
    general_comments: tuple[ReviewComment, ...] = ()

    @property
    def is_clean(self) -> bool:
        """Check if PR has zero failures, all threads resolved, no conflicts, and no blocker alerts."""
        if self.mergeable.lower() in ("dirty", "false", "conflicting"):
            return False
        checks_ok = all(
            c.conclusion.lower() in ("success", "skipped", "neutral")
            for c in self.check_runs
        )
        threads_ok = all(t.is_resolved for t in self.review_threads)
        alerts_ok = not any(
            a.severity.lower() in ("critical", "high", "error")
            for a in self.security_alerts
        )
        return checks_ok and threads_ok and alerts_ok


@dataclass(frozen=True)
class RepoStatus:
    """Comprehensive repository governance, permissions, and environments status."""

    name: str
    owner: str
    visibility: str
    private: bool
    default_branch: str
    allow_auto_merge: bool
    allow_squash_merge: bool
    has_pages: bool
    actions_enabled: bool
    allowed_actions: str
    default_workflow_permissions: str
    can_approve_pull_request_reviews: bool
    environments: tuple[str, ...] = ()
    required_status_checks: tuple[str, ...] = ()
    require_conversation_resolution: bool = False


@dataclass(frozen=True)
class ChecksReport:
    """CI check runs finding report."""

    ref_or_pr: str
    check_runs: tuple[CheckRunFinding, ...] = ()

    @property
    def has_failure(self) -> bool:
        """Return True if any check run concluded with failure."""
        return any(c.conclusion.lower() == "failure" for c in self.check_runs)


@dataclass(frozen=True)
class CodeScanningReport:
    """Aggregated code scanning findings or single alert inspection."""

    alerts: tuple[SecurityAlert, ...] = ()
    single_alert: SecurityAlert | None = None
    state: str = "open"


@dataclass(frozen=True)
class SecurityCommentsReport:
    """Pull request review and security threads report."""

    pr_number: int
    threads: tuple[ReviewThread, ...] = ()


@dataclass(frozen=True)
class ExaminePrReport:
    """Comprehensive PR summary report with optional failed logs."""

    summary: PrSummary
    show_details: bool = False
    failed_logs: dict[str, str] | None = None


# CQRS Commands


class ExaminePrCommand(Command):
    """Command requesting examination of a GitHub Pull Request."""

    pr_number: int | None = None
    show_details: bool = False


class InspectChecksCommand(Command):
    """Command requesting inspection of CI status checks for a PR or ref."""

    ref_or_pr: str


class InspectCodeScanningCommand(Command):
    """Command requesting inspection of GitHub code scanning / CodeQL alerts."""

    alert_number: int | None = None
    rule_filter: str | None = None
    package_filter: str | None = None
    severity_filter: str | None = None
    state: str = "open"


class InspectRepoCommand(Command):
    """Command requesting inspection of repository settings and governance."""

    repo_name: str | None = None


class InspectSecurityCommentsCommand(Command):
    """Command requesting inspection of review comments and security threads on a PR."""

    pr_number: int


__all__ = [
    "AlertSeverity",
    "CheckRunFinding",
    "ChecksReport",
    "CodeScanningReport",
    "ExaminePrCommand",
    "ExaminePrReport",
    "InspectChecksCommand",
    "InspectCodeScanningCommand",
    "InspectRepoCommand",
    "InspectSecurityCommentsCommand",
    "OutputFormat",
    "PrSummary",
    "RepoStatus",
    "ReviewComment",
    "ReviewThread",
    "SecurityAlert",
    "SecurityCommentsReport",
]
