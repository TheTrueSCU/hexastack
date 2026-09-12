"""Multi-format presenters for static analysis, security fuzzing, and snapshots.

Notes/Architectural Intent:
    Provides Rich interactive tables/panels, JSON, and Markdown presentation
    adapters for CodeQL scans, Atheris/OWASP fuzzing harnesses, and inline snapshots.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.domain.analysis import (
    CodeQlScanReport,
    FuzzRunReport,
    InlineSnapshotsReport,
)
from hexastack_tools.ports.analysis import AnalysisPresenterPort


class RichAnalysisPresenterAdapter(AnalysisPresenterPort):
    """Interactive Rich ANSI presenter for analysis tools."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize RichAnalysisPresenterAdapter with optional console."""
        self.console = console or Console()

    def present_codeql(self, report: CodeQlScanReport) -> int:
        """Render CodeQL scan results."""
        if not report.is_successful:
            self.console.print(
                Panel(
                    f"[bold red]CodeQL scan failed:\n{report.error_message}[/bold red]",
                    title="[bold red]CodeQL Analysis Error[/bold red]",
                )
            )
            return 1

        if report.sarif_path:
            self.console.print(
                Panel.fit(
                    f"[bold green]✨ CodeQL analysis completed successfully.\n"
                    f"SARIF output written to: {report.sarif_path}\n"
                    f"Findings: {report.findings_count} (Critical/High: {report.critical_count})[/bold green]",
                    border_style="green",
                )
            )
        return 0

    def present_fuzz(self, report: FuzzRunReport) -> int:
        """Render fuzz harness execution results."""
        table = Table(
            title="[bold cyan]Security & Coverage-Guided Fuzzing Metrics[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Target", style="bold")
        table.add_column("Engine", style="blue")
        table.add_column("Runs", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Crashes", justify="right")
        table.add_column("ReDoS Violations", justify="right")
        table.add_column("Status", justify="center")

        for r in report.results:
            status = (
                "[bold green]PASS[/bold green]"
                if r.passed
                else "[bold red]FAIL[/bold red]"
            )
            table.add_row(
                r.target,
                r.engine,
                str(r.runs),
                f"{r.duration_seconds}s",
                str(r.crashes),
                str(r.redos_violations),
                status,
            )

        self.console.print(table)
        if report.all_passed:
            self.console.print(
                Panel.fit(
                    "[bold green]✨ All fuzzing test harnesses completed without crashes or security violations.[/bold green]",
                    border_style="green",
                )
            )
            return 0

        self.console.print(
            Panel.fit(
                "[bold red]❌ One or more fuzzing targets detected crashes or violations.[/bold red]",
                border_style="red",
            )
        )
        return 1

    def present_inline_snapshots(self, report: InlineSnapshotsReport) -> int:
        """Render inline snapshot update outcome."""
        if report.exit_code == 0:
            self.console.print(
                f"[bold green]✨ Inline snapshots up to date across {len(report.targets_updated)} target(s).[/bold green]"
            )
        else:
            self.console.print(
                f"[bold red]❌ Inline snapshot update encountered errors (exit code: {report.exit_code}).[/bold red]"
            )
        return report.exit_code


class JsonAnalysisPresenterAdapter(AnalysisPresenterPort):
    """Machine-readable JSON presenter for analysis tools."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize JsonAnalysisPresenterAdapter."""
        self.console = console or Console()

    def present_codeql(self, report: CodeQlScanReport) -> int:
        """Format CodeQL scan report as JSON."""
        data = {
            "is_successful": report.is_successful,
            "sarif_path": str(report.sarif_path) if report.sarif_path else None,
            "findings_count": report.findings_count,
            "critical_count": report.critical_count,
            "error_message": report.error_message,
        }
        self.console.print_json(data=data)
        return 0 if report.is_successful else 1

    def present_fuzz(self, report: FuzzRunReport) -> int:
        """Format fuzz report as JSON."""
        data = {
            "all_passed": report.all_passed,
            "targets": [
                {
                    "target": r.target,
                    "engine": r.engine,
                    "runs": r.runs,
                    "duration_seconds": r.duration_seconds,
                    "crashes": r.crashes,
                    "redos_violations": r.redos_violations,
                    "passed": r.passed,
                }
                for r in report.results
            ],
        }
        self.console.print_json(data=data)
        return 0 if report.all_passed else 1

    def present_inline_snapshots(self, report: InlineSnapshotsReport) -> int:
        """Format snapshot report as JSON."""
        data = {
            "exit_code": report.exit_code,
            "targets_updated": list(report.targets_updated),
        }
        self.console.print_json(data=data)
        return report.exit_code


class MarkdownAnalysisPresenterAdapter(AnalysisPresenterPort):
    """GitHub Flavored Markdown presenter for CI step summaries."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize MarkdownAnalysisPresenterAdapter."""
        self.console = console or Console()

    def present_codeql(self, report: CodeQlScanReport) -> int:
        """Render CodeQL report as Markdown."""
        status = (
            "✅ Clean"
            if report.is_successful and report.critical_count == 0
            else "❌ Findings Detected"
        )
        lines = [
            f"### 🛡️ CodeQL SAST Security Scan: {status}",
            "",
            f"- **Findings**: {report.findings_count}",
            f"- **Critical/High**: {report.critical_count}",
        ]
        if report.sarif_path:
            lines.append(f"- **SARIF Artifact**: `{report.sarif_path}`")
        if report.error_message:
            lines.append(f"\n> [!ERROR]\n> {report.error_message}")
        lines.append("")
        self.console.print("\n".join(lines))
        return 0 if report.is_successful and report.critical_count == 0 else 1

    def present_fuzz(self, report: FuzzRunReport) -> int:
        """Render fuzz report as a Markdown table."""
        lines = [
            "### 🧪 Security & Fuzzing Harness Report",
            "",
            "| Target | Engine | Runs | Duration | Crashes | ReDoS | Status |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in report.results:
            status = "✅ Pass" if r.passed else "❌ Fail"
            lines.append(
                f"| `{r.target}` | `{r.engine}` | {r.runs} | {r.duration_seconds}s | {r.crashes} | {r.redos_violations} | {status} |"
            )
        lines.append("")
        self.console.print("\n".join(lines))
        return 0 if report.all_passed else 1

    def present_inline_snapshots(self, report: InlineSnapshotsReport) -> int:
        """Render snapshot report as Markdown."""
        status = "✅ Synced" if report.exit_code == 0 else "❌ Failed"
        lines = [
            f"### 📸 Inline Snapshots: {status}",
            "",
            f"- **Processed Targets**: {len(report.targets_updated)}",
            f"- **Exit Code**: {report.exit_code}",
            "",
        ]
        self.console.print("\n".join(lines))
        return report.exit_code


def create_analysis_presenter(
    format_name: str = "rich",
    console: Console | None = None,
) -> AnalysisPresenterPort:
    """Factory creating appropriate analysis presenter based on format string.

    Args:
        format_name: Output format ('rich', 'table', 'json', 'markdown').
        console: Optional Rich Console.

    Returns:
        AnalysisPresenterPort instance.
    """
    fmt = format_name.lower().strip()
    if fmt == "json":
        return JsonAnalysisPresenterAdapter(console=console)
    if fmt in ("markdown", "md"):
        return MarkdownAnalysisPresenterAdapter(console=console)
    return RichAnalysisPresenterAdapter(console=console)


__all__ = [
    "create_analysis_presenter",
    "JsonAnalysisPresenterAdapter",
    "MarkdownAnalysisPresenterAdapter",
    "RichAnalysisPresenterAdapter",
]
