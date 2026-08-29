"""Ports defining abstract interfaces for external tooling and VCS providers.

Notes/Architectural Intent:
    Decouples developer tooling commands and CI quality checks from concrete
    GitHub HTTP/REST/GraphQL API implementations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from hexastack_tools.domain.github import (
    CheckRunFinding,
    PrSummary,
    ReviewThread,
    SecurityAlert,
)

__all__ = [
    "GitHubApiPort",
]


@runtime_checkable
class GitHubApiPort(Protocol):
    """Port interface for communicating with GitHub APIs."""

    def get_pr_summary(self, pr_number: int) -> PrSummary:
        """Fetch comprehensive Pull Request summary including checks and reviews.

        Args:
            pr_number: GitHub Pull Request number.

        Returns:
            PrSummary domain model with checks, threads, and alerts.
        """

    def get_check_runs(self, ref: str) -> list[CheckRunFinding]:
        """Fetch check runs and commit statuses for a ref.

        Args:
            ref: Git commit SHA or branch reference.

        Returns:
            List of CheckRunFinding domain models.
        """

    def get_review_threads(self, pr_number: int) -> list[ReviewThread]:
        """Fetch review discussion threads and conversation resolution state.

        Args:
            pr_number: GitHub Pull Request number.

        Returns:
            List of ReviewThread models.
        """

    def get_code_scanning_alerts(
        self,
        ref: str | None = None,
        state: str = "open",
    ) -> list[SecurityAlert]:
        """Fetch CodeQL code scanning alerts.

        Args:
            ref: Optional Git branch or commit ref.
            state: Alert state filter ("open", "closed", "all").

        Returns:
            List of SecurityAlert models.
        """

    def get_single_alert(self, alert_number: int) -> SecurityAlert:
        """Fetch full metadata for a single security alert.

        Args:
            alert_number: GitHub security alert number.

        Returns:
            SecurityAlert domain model.
        """
