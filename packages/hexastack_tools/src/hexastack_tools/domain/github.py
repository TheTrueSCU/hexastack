"""Domain models and data contracts for developer tooling."""

from dataclasses import dataclass
from enum import StrEnum


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
    details_url: str
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
        """Check if PR has zero failures, all threads resolved, and no blocker alerts."""
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


__all__ = [
    "AlertSeverity",
    "CheckRunFinding",
    "OutputFormat",
    "PrSummary",
    "ReviewComment",
    "ReviewThread",
    "SecurityAlert",
]
