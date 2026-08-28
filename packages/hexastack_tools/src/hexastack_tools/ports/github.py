"""Ports defining abstract interfaces for external tooling and VCS providers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from hexastack_tools.domain.github import (
    CheckRunFinding,
    PRSummary,
    ReviewThread,
    SecurityAlert,
)


@runtime_checkable
class GitHubApiPort(Protocol):
    """Port interface for GitHub REST and GraphQL interactions."""

    def get_pr_summary(self, pr_number: int) -> PRSummary:
        """Fetch full aggregate summary for a pull request."""
        ...

    def get_check_runs(self, ref: str) -> list[CheckRunFinding]:
        """Fetch check runs and commit statuses for a ref."""
        ...

    def get_review_threads(self, pr_number: int) -> list[ReviewThread]:
        """Fetch review discussion threads and conversation resolution state."""
        ...

    def get_code_scanning_alerts(
        self,
        ref: str | None = None,
        state: str = "open",
    ) -> list[SecurityAlert]:
        """Fetch CodeQL code scanning alerts."""
        ...

    def get_single_alert(self, alert_number: int) -> SecurityAlert:
        """Fetch full metadata for a single security alert."""
        ...


__all__ = [
    "GitHubApiPort",
]
