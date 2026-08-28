"""Domain models and data contracts for developer tooling."""

from dataclasses import dataclass
from enum import StrEnum


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


@dataclass(frozen=True)
class ReviewThread:
    """A conversation thread attached to a PR review."""

    id: str
    is_resolved: bool
    resolved_by: str | None
    comments: tuple[ReviewComment, ...] = ()


@dataclass(frozen=True)
class SecurityAlert:
    """A security or quality alert from CodeQL, Scorecard, or Dependabot."""

    number: int
    rule_id: str
    rule_description: str
    severity: str
    security_severity_level: str | None
    state: str
    path: str
    start_line: int | None
    end_line: int | None
    message: str
    help_markdown: str | None = None


@dataclass(frozen=True)
class PRSummary:
    """Comprehensive aggregation of Pull Request state and governance checks."""

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
    scorecard_score: float | None = None

    @property
    def is_clean(self) -> bool:
        """Indicate whether PR has zero failed checks and zero unresolved threads."""
        has_failed_checks = any(
            c.conclusion.lower() == "failure" for c in self.check_runs
        )
        has_unresolved_threads = any(not t.is_resolved for t in self.review_threads)
        return not (has_failed_checks or has_unresolved_threads)


__all__ = [
    "AlertSeverity",
    "CheckRunFinding",
    "PRSummary",
    "ReviewComment",
    "ReviewThread",
    "SecurityAlert",
]
