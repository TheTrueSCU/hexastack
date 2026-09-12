"""Command handlers for GitHub PR inspection, status checks, repository settings, and CodeQL alerts.

Notes/Architectural Intent:
    Decouples driving GitHub CLI commands from concrete API implementations.
    Executes inspection queries through GitHubApiPort and produces immutable domain reports.
"""

from __future__ import annotations

import json
import subprocess

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
    RepoStatus,
    SecurityCommentsReport,
)
from hexastack_tools.ports.github import GitHubApiPort

__all__ = [
    "ExaminePrHandler",
    "InspectChecksHandler",
    "InspectCodeScanningHandler",
    "InspectRepoHandler",
    "InspectSecurityCommentsHandler",
]


class ExaminePrHandler:
    """Handler examining GitHub Pull Request health, review threads, and CI status."""

    def __init__(self, client: GitHubApiPort) -> None:
        """Initialize handler with GitHub API client port.

        Args:
            client: GitHubApiPort adapter instance.

        Notes/Architectural Intent:
            Relies strictly on the abstract port to allow mocking in unit tests
            without requiring real GitHub API credentials.
        """
        self._client = client

    @staticmethod
    def _discover_current_pr() -> int:
        """Auto-discover the open PR associated with current git branch using `gh` CLI.

        Returns:
            Discovered pull request number.

        Raises:
            RuntimeError: If PR cannot be auto-discovered.

        Notes/Architectural Intent:
            Provides fallback PR discovery using local git context when no explicit
            PR number is specified.
        """
        try:
            res = subprocess.run(
                ["gh", "pr", "view", "--json", "number"],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(res.stdout)
            pr_number = data.get("number")
            if isinstance(pr_number, int):
                return pr_number
        except Exception as exc:
            raise RuntimeError(
                "Could not auto-discover PR for current branch. Specify PR number."
            ) from exc
        raise RuntimeError("Could not determine PR number from gh CLI output.")

    def _fetch_failed_ci_logs(
        self, check_runs: tuple[CheckRunFinding, ...]
    ) -> dict[str, str]:
        """Extract failed CI logs from check runs.

        Args:
            check_runs: Tuple of CheckRunFinding instances.

        Returns:
            Dictionary mapping job names to log output snippets.

        Notes/Architectural Intent:
            Enriches PR failure reports with relevant log snippets for fast developer triage.
        """
        failed_logs: dict[str, str] = {}
        for c in check_runs:
            if c.conclusion.lower() != "failure":
                continue
            url = c.details_url
            if "/actions/runs/" not in url:
                continue
            try:
                run_id = url.split("/actions/runs/")[1].split("/")[0]
                if not run_id:
                    continue
                log_text = self._client.get_failed_run_logs(run_id)
                if log_text:
                    failed_logs[c.name] = log_text
            except (IndexError, ValueError):
                continue
        return failed_logs

    def handle(self, command: ExaminePrCommand) -> ExaminePrReport:
        """Handle ExaminePrCommand.

        Args:
            command: ExaminePrCommand specifying PR number and detail level.

        Returns:
            ExaminePrReport domain report.

        Notes/Architectural Intent:
            Orchestrates fetching PR summary and enriching failures with workflow logs.
        """
        target_pr = (
            command.pr_number
            if command.pr_number is not None
            else self._discover_current_pr()
        )
        summary = self._client.get_pr_summary(target_pr)
        failed_logs = self._fetch_failed_ci_logs(summary.check_runs)
        return ExaminePrReport(
            summary=summary,
            show_details=command.show_details,
            failed_logs=failed_logs if failed_logs else None,
        )


class InspectChecksHandler:
    """Handler querying CI status checks for a PR or Git ref."""

    def __init__(self, client: GitHubApiPort) -> None:
        """Initialize handler with GitHub API client port.

        Args:
            client: GitHubApiPort adapter instance.
        """
        self._client = client

    def handle(self, command: InspectChecksCommand) -> ChecksReport:
        """Handle InspectChecksCommand.

        Args:
            command: InspectChecksCommand specifying ref or PR number.

        Returns:
            ChecksReport domain report.

        Notes/Architectural Intent:
            Dispatches to either PR summary check runs or commit ref check runs based on
            identifier format.
        """
        if command.ref_or_pr.isdigit():
            summary = self._client.get_pr_summary(int(command.ref_or_pr))
            check_runs = tuple(summary.check_runs)
        else:
            check_runs = tuple(self._client.get_check_runs(command.ref_or_pr))
        return ChecksReport(ref_or_pr=command.ref_or_pr, check_runs=check_runs)


class InspectCodeScanningHandler:
    """Handler inspecting GitHub CodeQL code scanning alerts."""

    def __init__(self, client: GitHubApiPort) -> None:
        """Initialize handler with GitHub API client port.

        Args:
            client: GitHubApiPort adapter instance.
        """
        self._client = client

    def handle(self, command: InspectCodeScanningCommand) -> CodeScanningReport:
        """Handle InspectCodeScanningCommand.

        Args:
            command: InspectCodeScanningCommand with filter options.

        Returns:
            CodeScanningReport containing filtered alerts or single alert inspection.

        Notes/Architectural Intent:
            Applies client-side rule, severity, and package filtering to code scanning findings.
        """
        if command.alert_number is not None:
            alert = self._client.get_single_alert(command.alert_number)
            return CodeScanningReport(
                alerts=(alert,),
                single_alert=alert,
                state=command.state,
            )

        raw_alerts = self._client.get_code_scanning_alerts(state=command.state)
        filtered = list(raw_alerts)
        if command.rule_filter:
            rule_lower = command.rule_filter.lower()
            filtered = [a for a in filtered if rule_lower in a.rule_id.lower()]
        if command.severity_filter:
            sev_lower = command.severity_filter.lower()
            filtered = [a for a in filtered if a.severity.lower() == sev_lower]
        if command.package_filter:
            pkg_lower = command.package_filter.lower()
            filtered = [a for a in filtered if pkg_lower in a.path.lower()]

        return CodeScanningReport(
            alerts=tuple(filtered),
            single_alert=None,
            state=command.state,
        )


class InspectRepoHandler:
    """Handler inspecting GitHub repository governance, settings, and environments."""

    def __init__(self, client: GitHubApiPort) -> None:
        """Initialize handler with GitHub API client port.

        Args:
            client: GitHubApiPort adapter instance.
        """
        self._client = client

    def handle(self, command: InspectRepoCommand) -> RepoStatus:
        """Handle InspectRepoCommand.

        Args:
            command: InspectRepoCommand specifying optional repo name.

        Returns:
            RepoStatus domain model.

        Notes/Architectural Intent:
            Parses owner/repo target and delegates to repository status inspection port.
        """
        owner: str | None = None
        target_repo: str | None = None
        if command.repo_name:
            if "/" in command.repo_name:
                owner, target_repo = command.repo_name.split("/", 1)
            else:
                target_repo = command.repo_name
        return self._client.get_repo_status(owner=owner, repo=target_repo)


class InspectSecurityCommentsHandler:
    """Handler inspecting review discussions and security comments on a PR."""

    def __init__(self, client: GitHubApiPort) -> None:
        """Initialize handler with GitHub API client port.

        Args:
            client: GitHubApiPort adapter instance.
        """
        self._client = client

    def handle(self, command: InspectSecurityCommentsCommand) -> SecurityCommentsReport:
        """Handle InspectSecurityCommentsCommand.

        Args:
            command: InspectSecurityCommentsCommand specifying PR number.

        Returns:
            SecurityCommentsReport domain model.

        Notes/Architectural Intent:
            Gathers review threads and comments for PR security inspection.
        """
        summary = self._client.get_pr_summary(command.pr_number)
        return SecurityCommentsReport(
            pr_number=command.pr_number,
            threads=summary.review_threads,
        )
