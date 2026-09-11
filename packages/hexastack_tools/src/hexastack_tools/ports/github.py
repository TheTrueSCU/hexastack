"""Ports defining abstract interfaces for external tooling and VCS providers.

Notes/Architectural Intent:
    Decouples developer tooling commands and CI quality checks from concrete
    GitHub HTTP/REST/GraphQL API implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from hexastack_tools.domain.github import (
    CheckRunFinding,
    ChecksReport,
    CodeScanningReport,
    ExaminePrReport,
    PrSummary,
    RepoStatus,
    ReviewThread,
    SecurityAlert,
    SecurityCommentsReport,
)

__all__ = [
    "GitHubApiPort",
    "GitHubPresenterPort",
]


@runtime_checkable
class GitHubApiPort(Protocol):
    """Port interface for communicating with GitHub APIs."""

    def get_repo_status(
        self,
        owner: str | None = None,
        repo: str | None = None,
    ) -> RepoStatus:
        """Fetch repository configuration, settings, permissions, and environments.

        Args:
            owner: Optional repository owner (defaults to adapter config).
            repo: Optional repository name (defaults to adapter config).

        Returns:
            RepoStatus domain model.
        """

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

    def get_failed_run_logs(self, run_id: int | str) -> str | None:
        """Fetch failed log snippets for a specific workflow run.

        Args:
            run_id: GitHub Actions workflow run database ID.

        Returns:
            String log snippet or None if not accessible.
        """

    def get_workflow_runs(
        self,
        branch: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Fetch recent workflow runs for a branch.

        Args:
            branch: Optional branch name filter.
            limit: Maximum number of runs to fetch.

        Returns:
            List of workflow run summary dictionaries.
        """


class GitHubPresenterPort(ABC):
    """Abstract port interface for presenting GitHub inspection diagnostics."""

    @abstractmethod
    def present_pr_summary(self, report: ExaminePrReport) -> int:
        """Render comprehensive Pull Request summary dashboard.

        Args:
            report: ExaminePrReport domain model.

        Returns:
            Exit code (0 if clean/healthy, 1 if blocked or has failures).
        """

    @abstractmethod
    def present_checks(self, report: ChecksReport) -> int:
        """Render CI check runs status table.

        Args:
            report: ChecksReport domain model.

        Returns:
            Exit code (0 if all passed, 1 if any check failed).
        """

    @abstractmethod
    def present_repo_status(self, status: RepoStatus) -> int:
        """Render repository governance and permissions status.

        Args:
            status: RepoStatus domain model.

        Returns:
            Exit code (0 for success).
        """

    @abstractmethod
    def present_security_comments(self, report: SecurityCommentsReport) -> int:
        """Render PR review threads and security discussion comments.

        Args:
            report: SecurityCommentsReport domain model.

        Returns:
            Exit code (0 for success).
        """

    @abstractmethod
    def present_code_scanning(self, report: CodeScanningReport) -> int:
        """Render CodeQL security alerts and remediation details.

        Args:
            report: CodeScanningReport domain model.

        Returns:
            Exit code (0 for success).
        """
