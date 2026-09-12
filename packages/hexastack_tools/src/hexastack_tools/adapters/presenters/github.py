"""Multi-format presenters for GitHub PRs, status checks, repository settings, and CodeQL alerts.

Notes/Architectural Intent:
    Decouples GitHub API report presentation from driving CLI commands, enabling
    interactive Rich console tables, machine-readable JSON outputs, and Markdown
    formatting for CI environments.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.adapters.presenters.checks import present_checks
from hexastack_tools.adapters.presenters.pr import present_pr_summary
from hexastack_tools.adapters.presenters.repo import present_repo_status
from hexastack_tools.adapters.presenters.security import present_security_comments
from hexastack_tools.domain.github import (
    ChecksReport,
    CodeScanningReport,
    ExaminePrReport,
    OutputFormat,
    RepoStatus,
    SecurityCommentsReport,
)
from hexastack_tools.ports.github import GitHubPresenterPort

__all__ = [
    "create_github_presenter",
    "JsonGitHubPresenterAdapter",
    "MarkdownGitHubPresenterAdapter",
    "RichGitHubPresenterAdapter",
]


class RichGitHubPresenterAdapter(GitHubPresenterPort):
    """Rich interactive console presenter for GitHub inspection findings."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional Rich console.

        Args:
            console: Optional Rich Console instance.
        """
        self._console = console or Console()

    def present_pr_summary(self, report: ExaminePrReport) -> int:
        """Render comprehensive Pull Request summary dashboard."""
        present_pr_summary(
            report.summary,
            output_format=OutputFormat.RICH,
            show_details=report.show_details,
            failed_logs=report.failed_logs,
        )
        return 0 if report.summary.is_clean else 1

    def present_checks(self, report: ChecksReport) -> int:
        """Render CI check runs status table."""
        present_checks(
            list(report.check_runs), report.ref_or_pr, output_format=OutputFormat.RICH
        )
        return 1 if report.has_failure else 0

    def present_repo_status(self, status: RepoStatus) -> int:
        """Render repository governance and permissions status."""
        present_repo_status(status, output_format=OutputFormat.RICH)
        return 0

    def present_security_comments(self, report: SecurityCommentsReport) -> int:
        """Render PR review threads and security discussion comments."""
        present_security_comments(
            report.threads, report.pr_number, output_format=OutputFormat.RICH
        )
        return 0

    def present_code_scanning(self, report: CodeScanningReport) -> int:
        """Render CodeQL security alerts and remediation details."""
        if report.single_alert:
            alert = report.single_alert
            panel_content = (
                f"[bold white]Rule ID:[/bold white] [bold cyan]{alert.rule_id}[/bold cyan]\n"
                f"[bold white]Severity:[/bold white] {alert.severity} ({alert.security_severity_level or 'quality'})\n"
                f"[bold white]Location:[/bold white] [bold blue]{alert.path}:{alert.start_line}-{alert.end_line}[/bold blue]\n"
                f"[bold white]State:[/bold white] {alert.state}\n\n"
                f"[bold white]Message:[/bold white]\n{alert.message}\n\n"
                f"[bold white]Description:[/bold white]\n{alert.rule_description}\n"
            )
            if alert.help_markdown:
                panel_content += f"\n[bold white]Remediation Guidance:[/bold white]\n{alert.help_markdown[:400]}..."

            self._console.print(
                Panel(
                    panel_content,
                    title=f"[bold magenta]CodeQL Alert #{alert.number}[/bold magenta]",
                    border_style="cyan",
                )
            )
            return 0

        if not report.alerts:
            self._console.print(
                f"[bold green]✨ No {report.state} CodeQL alerts found.[/bold green]"
            )
            return 0

        table = Table(
            title=f"[bold cyan]CodeQL Alerts Summary (State: {report.state}, Total: {len(report.alerts)})[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Rule ID", style="bold")
        table.add_column("Severity", width=12)
        table.add_column("Location", style="cyan")
        table.add_column("Description")

        for a in report.alerts[:50]:
            table.add_row(
                a.rule_id,
                a.severity,
                f"{a.path}:{a.start_line}",
                a.rule_description[:60],
            )
        self._console.print(table)
        if len(report.alerts) > 50:
            self._console.print(
                f"[dim]... and {len(report.alerts) - 50} more alerts[/dim]"
            )
        return 0


class JsonGitHubPresenterAdapter(GitHubPresenterPort):
    """Machine-readable JSON presenter for GitHub findings."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional Rich console.

        Args:
            console: Optional Rich Console instance.
        """
        self._console = console or Console()

    def present_pr_summary(self, report: ExaminePrReport) -> int:
        """Output PR summary as JSON."""
        data: dict[str, Any] = {
            "summary": asdict(report.summary),
            "show_details": report.show_details,
            "failed_logs": report.failed_logs or {},
            "is_clean": report.summary.is_clean,
        }
        self._console.print(json.dumps(data, indent=2))
        return 0 if report.summary.is_clean else 1

    def present_checks(self, report: ChecksReport) -> int:
        """Output CI checks as JSON."""
        data = {
            "ref_or_pr": report.ref_or_pr,
            "has_failure": report.has_failure,
            "checks": [asdict(c) for c in report.check_runs],
        }
        self._console.print(json.dumps(data, indent=2))
        return 1 if report.has_failure else 0

    def present_repo_status(self, status: RepoStatus) -> int:
        """Output repository governance status as JSON."""
        self._console.print(json.dumps(asdict(status), indent=2))
        return 0

    def present_security_comments(self, report: SecurityCommentsReport) -> int:
        """Output PR security comments as JSON."""
        data = {
            "pr_number": report.pr_number,
            "threads": [asdict(t) for t in report.threads],
        }
        self._console.print(json.dumps(data, indent=2))
        return 0

    def present_code_scanning(self, report: CodeScanningReport) -> int:
        """Output CodeQL alerts as JSON."""
        data: dict[str, Any] = {
            "state": report.state,
            "count": len(report.alerts),
            "alerts": [asdict(a) for a in report.alerts],
        }
        if report.single_alert:
            data["single_alert"] = asdict(report.single_alert)
        self._console.print(json.dumps(data, indent=2))
        return 0


class MarkdownGitHubPresenterAdapter(GitHubPresenterPort):
    """Markdown formatted presenter for GitHub diagnostics in CI/CD summaries."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional Rich console.

        Args:
            console: Optional Rich Console instance.
        """
        self._console = console or Console()

    def present_pr_summary(self, report: ExaminePrReport) -> int:
        """Format PR summary as GitHub Flavored Markdown."""
        s = report.summary
        status_icon = "✅" if s.is_clean else "❌"
        lines = [
            f"# {status_icon} Pull Request #{s.number}: {s.title}",
            "",
            f"- **Author**: @{s.author}",
            f"- **State**: {s.state} (mergeable: `{s.mergeable}`)",
            f"- **Branches**: `{s.head_ref}` ➔ `{s.base_ref}`",
            f"- **URL**: {s.html_url}",
            "",
            "## CI Check Runs",
            "",
            "| Job / Check Name | Status | Conclusion | Details |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for c in s.check_runs:
            c_icon = (
                "✅"
                if c.conclusion == "success"
                else ("❌" if c.conclusion == "failure" else "⏳")
            )
            lines.append(
                f"| {c.name} | {c.status} | {c_icon} {c.conclusion} | [View]({c.details_url}) |"
            )

        if s.review_threads:
            lines.extend(
                [
                    "",
                    f"## Review Threads ({len(s.review_threads)} total)",
                    "",
                    "| Thread ID | Resolved | Resolved By |",
                    "| :--- | :--- | :--- |",
                ]
            )
            for t in s.review_threads:
                r_icon = "✅" if t.is_resolved else "⚠️ Unresolved"
                lines.append(f"| `{t.id}` | {r_icon} | {t.resolved_by or '-'} |")

        self._console.print("\n".join(lines))
        return 0 if s.is_clean else 1

    def present_checks(self, report: ChecksReport) -> int:
        """Format CI checks as Markdown."""
        lines = [
            f"# CI Status Checks for `{report.ref_or_pr}`",
            "",
            "| Check Name | Status | Conclusion | Details |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for c in report.check_runs:
            c_icon = (
                "✅"
                if c.conclusion == "success"
                else ("❌" if c.conclusion == "failure" else "⏳")
            )
            lines.append(
                f"| {c.name} | {c.status} | {c_icon} {c.conclusion} | [Details]({c.details_url}) |"
            )
        self._console.print("\n".join(lines))
        return 1 if report.has_failure else 0

    def present_repo_status(self, status: RepoStatus) -> int:
        """Format repository status as Markdown."""
        lines = [
            f"# Repository Status: {status.owner}/{status.name}",
            "",
            f"- **Visibility**: {status.visibility} (private: `{status.private}`)",
            f"- **Default Branch**: `{status.default_branch}`",
            f"- **Actions Enabled**: `{status.actions_enabled}`",
            f"- **Auto-Merge**: `{status.allow_auto_merge}`",
            f"- **Squash Merge**: `{status.allow_squash_merge}`",
            "",
            "## Required Status Checks",
            "",
        ]
        for chk in status.required_status_checks:
            lines.append(f"- `{chk}`")
        self._console.print("\n".join(lines))
        return 0

    def present_security_comments(self, report: SecurityCommentsReport) -> int:
        """Format PR security comments as Markdown."""
        lines = [
            f"# Review & Security Comments for PR #{report.pr_number}",
            "",
            f"Total review threads: {len(report.threads)}",
            "",
        ]
        for t in report.threads:
            lines.append(
                f"### Thread `{t.id}` ({'Resolved' if t.is_resolved else 'Unresolved'})"
            )
            for c in t.comments:
                lines.append(f"- **@{c.author}** ({c.created_at}): {c.body[:200]}")
            lines.append("")
        self._console.print("\n".join(lines))
        return 0

    def present_code_scanning(self, report: CodeScanningReport) -> int:
        """Format CodeQL alerts as Markdown."""
        if report.single_alert:
            a = report.single_alert
            lines = [
                f"# CodeQL Alert #{a.number}: {a.rule_id}",
                "",
                f"- **Severity**: `{a.severity}`",
                f"- **Location**: `{a.path}:{a.start_line}-{a.end_line}`",
                f"- **State**: `{a.state}`",
                f"- **Description**: {a.rule_description}",
                "",
                "## Message",
                f"{a.message}",
            ]
            self._console.print("\n".join(lines))
            return 0

        lines = [
            f"# CodeQL Alerts (State: `{report.state}`, Total: {len(report.alerts)})",
            "",
            "| Rule ID | Severity | Location | Description |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for a in report.alerts[:50]:
            lines.append(
                f"| `{a.rule_id}` | `{a.severity}` | `{a.path}:{a.start_line}` | {a.rule_description[:60]} |"
            )
        self._console.print("\n".join(lines))
        return 0


def create_github_presenter(
    format_name: str = "table",
    output_format: str | None = None,
    console: Console | None = None,
) -> GitHubPresenterPort:
    """Factory creating GitHubPresenterPort adapter based on format string.

    Args:
        format_name: One of 'table', 'rich', 'json', 'markdown', 'plain'.
        output_format: Optional alternative format argument name.
        console: Optional Rich Console instance.

    Returns:
        Configured GitHubPresenterPort adapter instance.
    """
    raw_fmt = output_format if output_format is not None else format_name
    fmt = raw_fmt.lower().strip()
    if fmt in ("json",):
        return JsonGitHubPresenterAdapter(console=console)
    if fmt in ("markdown", "md"):
        return MarkdownGitHubPresenterAdapter(console=console)
    return RichGitHubPresenterAdapter(console=console)
