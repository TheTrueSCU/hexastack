"""Multi-format presenters for PyPI distribution builds, checks, publishing, and reproducible audits.

Notes/Architectural Intent:
    Decouples domain report presentation from CLI commands, providing interactive Rich
    tables, structured JSON outputs, and Markdown summaries for CI environments.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from hexastack_tools.domain.pypi import (
    PyPiBuildReport,
    PyPiCheckReport,
    PyPiPublishReport,
    ReproducibleBuildReport,
)
from hexastack_tools.ports.pypi import PyPiPresenterPort

__all__ = [
    "create_pypi_presenter",
    "JsonPyPiPresenterAdapter",
    "MarkdownPyPiPresenterAdapter",
    "RichPyPiPresenterAdapter",
]


class RichPyPiPresenterAdapter(PyPiPresenterPort):
    """Rich interactive console presenter for PyPI diagnostics."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with Rich console instance.

        Args:
            console: Optional Rich console.
        """
        self._console = console or Console()

    def present_check(self, report: PyPiCheckReport) -> int:
        """Render package release availability status table."""
        table = Table(
            title="[bold cyan]PyPI Release Version Availability Checker[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Package Name", style="bold")
        table.add_column("Local Version", width=14)
        table.add_column("PyPI Status", width=24)

        for c in report.checks:
            status_styled = (
                "[yellow]Already Released[/yellow]"
                if c.exists
                else "[bold green]Available for Release[/bold green]"
            )
            table.add_row(c.package.name, c.package.version, status_styled)

        self._console.print(table)
        return 0

    def present_build(self, report: PyPiBuildReport) -> int:
        """Render package distribution build report."""
        table = Table(
            title=f"[bold cyan]PyPI Monorepo Distribution Builder -> {report.target_dist}[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Package Name", style="bold")
        table.add_column("Version", width=12)
        table.add_column("Status", width=16)

        for r in report.results:
            status = (
                "[bold green]✓ Built[/bold green]"
                if r.success
                else "[bold red]✗ Failed[/bold red]"
            )
            table.add_row(r.package.name, r.package.version, status)

        self._console.print(table)
        return 1 if report.has_failure else 0

    def present_publish(self, report: PyPiPublishReport) -> int:
        """Render package publication report."""
        table = Table(
            title="[bold cyan]PyPI Smart Publisher[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Package Name", style="bold")
        table.add_column("Version", width=12)
        table.add_column("Status", width=36)

        for r in report.results:
            if r.outcome == "published":
                status = "[bold green]✓ Published[/bold green]"
            elif r.outcome == "skipped":
                detail = f" ({r.detail})" if r.detail else ""
                status = f"[bold yellow]Skipped{detail}[/bold yellow]"
            else:
                detail = f" ({r.detail})" if r.detail else ""
                status = f"[bold red]Failed{detail}[/bold red]"
            table.add_row(r.package.name, r.package.version, status)

        self._console.print(table)
        counts = report.counts
        self._console.print(
            f"\n[bold]Summary:[/bold] {counts['published']} published, {counts['skipped']} skipped, {counts['failed']} failed."
        )
        return 1 if report.has_failure else 0

    def present_reproducible(self, report: ReproducibleBuildReport) -> int:
        """Render byte-for-byte reproducible build audit report."""
        table = Table(
            title=f"[bold cyan]PyPI Reproducible Build Auditor (SOURCE_DATE_EPOCH={report.epoch})[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Package Name", style="bold")
        table.add_column("Artifact File", style="cyan")
        table.add_column("SHA-256 (Run 1 / Run 2)", style="dim")
        table.add_column("Reproducibility", width=18)

        for r in report.results:
            repro_styled = (
                "[bold green]✓ Reproducible[/bold green]"
                if r.is_reproducible
                else "[bold red]✗ Mismatch[/bold red]"
            )
            h_info = (
                f"{r.hash1[:16]}..."
                if r.is_reproducible
                else f"{r.hash1[:8]} != {r.hash2[:8]}"
            )
            table.add_row(r.package_name, r.artifact_name, h_info, repro_styled)

        self._console.print(table)
        if report.all_matched:
            self._console.print(
                "[bold green]All package distributions are 100% byte-for-byte reproducible![/bold green]"
            )
            return 0
        self._console.print(
            "[bold red]One or more package distributions produced non-deterministic outputs.[/bold red]"
        )
        return 1


class JsonPyPiPresenterAdapter(PyPiPresenterPort):
    """Machine-readable JSON presenter for PyPI diagnostics."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional console for raw output printing."""
        self._console = console or Console()

    def present_check(self, report: PyPiCheckReport) -> int:
        """Render package release availability as JSON."""
        data = {
            "checks": [
                {
                    "package": c.package.name,
                    "version": c.package.version,
                    "exists": c.exists,
                }
                for c in report.checks
            ]
        }
        self._console.print_json(data=data)
        return 0

    def present_build(self, report: PyPiBuildReport) -> int:
        """Render package build report as JSON."""
        data = {
            "target_dist": str(report.target_dist),
            "has_failure": report.has_failure,
            "results": [
                {
                    "package": r.package.name,
                    "version": r.package.version,
                    "success": r.success,
                    "output": r.output,
                }
                for r in report.results
            ],
        }
        self._console.print_json(data=data)
        return 1 if report.has_failure else 0

    def present_publish(self, report: PyPiPublishReport) -> int:
        """Render package publication report as JSON."""
        data = {
            "counts": report.counts,
            "has_failure": report.has_failure,
            "results": [
                {
                    "package": r.package.name,
                    "version": r.package.version,
                    "outcome": r.outcome,
                    "is_success": r.is_success,
                    "detail": r.detail,
                }
                for r in report.results
            ],
        }
        self._console.print_json(data=data)
        return 1 if report.has_failure else 0

    def present_reproducible(self, report: ReproducibleBuildReport) -> int:
        """Render reproducible build audit as JSON."""
        data = {
            "epoch": report.epoch,
            "all_matched": report.all_matched,
            "results": [
                {
                    "package": r.package_name,
                    "artifact": r.artifact_name,
                    "hash1": r.hash1,
                    "hash2": r.hash2,
                    "is_reproducible": r.is_reproducible,
                }
                for r in report.results
            ],
        }
        self._console.print_json(data=data)
        return 0 if report.all_matched else 1


class MarkdownPyPiPresenterAdapter(PyPiPresenterPort):
    """Markdown formatted presenter for PyPI diagnostics."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional console."""
        self._console = console or Console()

    def present_check(self, report: PyPiCheckReport) -> int:
        """Render package release availability as Markdown."""
        lines = [
            "### PyPI Release Version Availability",
            "",
            "| Package | Version | Status |",
            "|---|---|---|",
        ]
        for c in report.checks:
            status = "Already Released" if c.exists else "Available for Release"
            lines.append(f"| `{c.package.name}` | {c.package.version} | {status} |")
        self._console.print("\n".join(lines))
        return 0

    def present_build(self, report: PyPiBuildReport) -> int:
        """Render package build report as Markdown."""
        lines = [
            f"### PyPI Monorepo Distribution Builder (`{report.target_dist}`)",
            "",
            "| Package | Version | Status |",
            "|---|---|---|",
        ]
        for r in report.results:
            status = "✓ Built" if r.success else "✗ Failed"
            lines.append(f"| `{r.package.name}` | {r.package.version} | {status} |")
        self._console.print("\n".join(lines))
        return 1 if report.has_failure else 0

    def present_publish(self, report: PyPiPublishReport) -> int:
        """Render package publication report as Markdown."""
        counts = report.counts
        lines = [
            "### PyPI Publication Report",
            "",
            f"**Summary:** {counts['published']} published, {counts['skipped']} skipped, {counts['failed']} failed.",
            "",
            "| Package | Version | Outcome |",
            "|---|---|---|",
        ]
        for r in report.results:
            lines.append(f"| `{r.package.name}` | {r.package.version} | {r.outcome} |")
        self._console.print("\n".join(lines))
        return 1 if report.has_failure else 0

    def present_reproducible(self, report: ReproducibleBuildReport) -> int:
        """Render reproducible build audit as Markdown."""
        status_msg = (
            "**All package distributions are 100% byte-for-byte reproducible!**"
            if report.all_matched
            else "**One or more package distributions produced non-deterministic outputs.**"
        )
        lines = [
            f"### PyPI Reproducible Build Auditor (epoch: `{report.epoch}`)",
            "",
            status_msg,
            "",
            "| Package | Artifact | Status |",
            "|---|---|---|",
        ]
        for r in report.results:
            status = "✓ Reproducible" if r.is_reproducible else "✗ Mismatch"
            lines.append(f"| `{r.package_name}` | `{r.artifact_name}` | {status} |")
        self._console.print("\n".join(lines))
        return 0 if report.all_matched else 1


def create_pypi_presenter(
    output_format: str | None = None,
    console: Console | None = None,
) -> PyPiPresenterPort:
    """Factory creating appropriate PyPiPresenterPort implementation.

    Args:
        output_format: Desired format string ('json', 'markdown', or 'rich'/'table').
        console: Optional Rich console instance.

    Returns:
        Configured PyPiPresenterPort implementation.
    """
    fmt = (output_format or "rich").lower()
    if fmt == "json":
        return JsonPyPiPresenterAdapter(console=console)
    if fmt == "markdown":
        return MarkdownPyPiPresenterAdapter(console=console)
    return RichPyPiPresenterAdapter(console=console)
