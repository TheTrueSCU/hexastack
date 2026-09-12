"""Multi-format presenters for architecture and documentation generators.

Notes/Architectural Intent:
    Provides Rich interactive, JSON machine-readable, and GitHub Flavored Markdown
    presentation adapters for pydeps diagram generation, USAGE.md catalog synchronization,
    and pytest-archon test scaffolding.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.domain.generators import (
    ArchonReport,
    PydepsReport,
    UsageDocsReport,
)
from hexastack_tools.ports.generators import GeneratorPresenterPort


class RichGeneratorPresenterAdapter(GeneratorPresenterPort):
    """Interactive ANSI terminal presenter for generators using Rich."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize RichGeneratorPresenterAdapter with optional console.

        Args:
            console: Rich Console instance or None to instantiate default.
        """
        self.console = console or Console()

    def present_pydeps(self, report: PydepsReport) -> int:
        """Render generated pydeps diagrams in a formatted table.

        Args:
            report: PydepsReport to render.

        Returns:
            0 if generation was successful, 1 otherwise.

        Notes/Architectural Intent:
            Displays a colorized summary table listing all generated SVG diagram
            assets and total count.
        """
        table = Table(
            title="[bold cyan]Architecture Dependency Diagram Generator (pydeps)[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Asset / Package", style="bold")
        table.add_column("Output File", style="blue")

        for res in report.results:
            table.add_row(res.name, res.path)

        self.console.print(table)
        if report.is_successful:
            self.console.print(
                Panel.fit(
                    f"[bold green]✨ Generated {len(report.results)} architecture dependency diagram(s) in docs/assets/pydeps/.[/bold green]",
                    border_style="green",
                )
            )
            return 0

        self.console.print(
            Panel.fit(
                "[bold red]❌ One or more architecture diagrams failed to generate.[/bold red]",
                border_style="red",
            )
        )
        return 1

    def present_usage_docs(self, report: UsageDocsReport) -> int:
        """Render USAGE.md validation or update results.

        Args:
            report: UsageDocsReport containing status and diffs.

        Returns:
            0 if documentation is valid/current, 1 if out of date.

        Notes/Architectural Intent:
            Emits clear feedback with diffs when USAGE.md files are out of sync.
        """
        for f in report.up_to_date_files:
            self.console.print(f"[bold green]✓[/bold green] {f} is up to date.")
        for f in report.updated_files:
            self.console.print(f"[bold green]✓[/bold green] Updated {f}")
        for f in report.stale_files:
            self.console.print(
                f"[bold red]❌ {f} is out of date. Run 'uv run generate-usage-docs --fix' to update.[/bold red]"
            )

        for _, diff_text in report.diffs:
            self.console.print(diff_text)

        return 0 if report.is_valid else 1

    def present_archon(self, report: ArchonReport) -> int:
        """Render pytest-archon test scaffolding summary.

        Args:
            report: ArchonReport containing created files.

        Returns:
            0 if successful, 1 if failure.

        Notes/Architectural Intent:
            Informs the developer about created or skipped architecture boundary tests.
        """
        for f in report.generated_files:
            self.console.print(
                f"[bold green]✓[/bold green] Scaffolded boundary tests in {f}"
            )
        for s in report.skipped_files:
            self.console.print(
                f"[dim]Skipped {s} (no standard hexagonal layers present)[/dim]"
            )
        return 0 if report.is_successful else 1


class JsonGeneratorPresenterAdapter(GeneratorPresenterPort):
    """Machine-readable JSON presenter for generator outputs."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize JsonGeneratorPresenterAdapter."""
        self.console = console or Console()

    def present_pydeps(self, report: PydepsReport) -> int:
        """Format pydeps report as structured JSON."""
        data = {
            "is_successful": report.is_successful,
            "total_diagrams": len(report.results),
            "diagrams": [
                {"name": r.name, "path": r.path, "success": r.success}
                for r in report.results
            ],
        }
        self.console.print_json(data=data)
        return 0 if report.is_successful else 1

    def present_usage_docs(self, report: UsageDocsReport) -> int:
        """Format USAGE.md report as structured JSON."""
        data = {
            "is_valid": report.is_valid,
            "up_to_date_files": list(report.up_to_date_files),
            "updated_files": list(report.updated_files),
            "stale_files": list(report.stale_files),
            "diffs": dict(report.diffs),
        }
        self.console.print_json(data=data)
        return 0 if report.is_valid else 1

    def present_archon(self, report: ArchonReport) -> int:
        """Format pytest-archon report as structured JSON."""
        data = {
            "is_successful": report.is_successful,
            "generated_files": list(report.generated_files),
            "skipped_files": list(report.skipped_files),
        }
        self.console.print_json(data=data)
        return 0 if report.is_successful else 1


class MarkdownGeneratorPresenterAdapter(GeneratorPresenterPort):
    """GitHub Flavored Markdown presenter for CI step summaries."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize MarkdownGeneratorPresenterAdapter."""
        self.console = console or Console()

    def present_pydeps(self, report: PydepsReport) -> int:
        """Render pydeps diagrams as a Markdown table."""
        lines = [
            "### 📐 Architecture Dependency Diagrams",
            "",
            "| Asset / Package | Output File | Status |",
            "|---|---|---|",
        ]
        for r in report.results:
            status = "✅ Generated" if r.success else "❌ Failed"
            lines.append(f"| `{r.name}` | `{r.path}` | {status} |")
        lines.append("")
        self.console.print("\n".join(lines))
        return 0 if report.is_successful else 1

    def present_usage_docs(self, report: UsageDocsReport) -> int:
        """Render USAGE.md status as Markdown."""
        status = "✅ Up to date" if report.is_valid else "❌ Out of date"
        lines = [
            f"### 📖 USAGE.md Verification: {status}",
            "",
            f"- **Up to date**: {len(report.up_to_date_files)} file(s)",
            f"- **Updated**: {len(report.updated_files)} file(s)",
            f"- **Stale**: {len(report.stale_files)} file(s)",
            "",
        ]
        if report.diffs:
            lines.append("<details><summary>View Diffs</summary>\n")
            for f, diff_text in report.diffs:
                lines.append(f"#### `{f}`")
                lines.append(f"```diff\n{diff_text}\n```")
            lines.append("</details>\n")

        self.console.print("\n".join(lines))
        return 0 if report.is_valid else 1

    def present_archon(self, report: ArchonReport) -> int:
        """Render pytest-archon results as Markdown."""
        lines = [
            "### 🏛️ Hexagonal Boundary Test Scaffolding",
            "",
            f"- **Generated**: {len(report.generated_files)} file(s)",
            f"- **Skipped**: {len(report.skipped_files)} file(s)",
            "",
        ]
        for f in report.generated_files:
            lines.append(f"- Generated: `{f}`")
        self.console.print("\n".join(lines))
        return 0 if report.is_successful else 1


def create_generator_presenter(
    format_name: str = "rich",
    console: Console | None = None,
) -> GeneratorPresenterPort:
    """Factory creating appropriate generator presenter based on format string.

    Args:
        format_name: Output format name ('rich', 'table', 'json', 'markdown').
        console: Optional Rich Console instance.

    Returns:
        GeneratorPresenterPort instance conforming to requested format.

    Notes/Architectural Intent:
        Encapsulates presenter selection so CLI entrypoints remain agnostic of
        concrete output format adapters.
    """
    fmt = format_name.lower().strip()
    if fmt == "json":
        return JsonGeneratorPresenterAdapter(console=console)
    if fmt in ("markdown", "md"):
        return MarkdownGeneratorPresenterAdapter(console=console)
    return RichGeneratorPresenterAdapter(console=console)


__all__ = [
    "create_generator_presenter",
    "JsonGeneratorPresenterAdapter",
    "MarkdownGeneratorPresenterAdapter",
    "RichGeneratorPresenterAdapter",
]
