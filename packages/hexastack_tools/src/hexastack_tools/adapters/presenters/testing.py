"""Multi-format presenters for mutation testing, boundary audits, and test impact analysis.

Notes/Architectural Intent:
    Decouples mutation triage reports, layer leak diagnostics, and impact analysis
    from console rendering, enabling interactive Rich UI, machine-readable JSON,
    and Markdown for GitHub Actions summaries.
"""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.domain.testing import (
    BoundaryAuditReport,
    ImpactedTestsReport,
    MutationAuditReport,
    RedundancyAuditReport,
)
from hexastack_tools.ports.testing import TestingPresenterPort

__all__ = [
    "create_testing_presenter",
    "JsonTestingPresenterAdapter",
    "MarkdownTestingPresenterAdapter",
    "RichTestingPresenterAdapter",
]


class RichTestingPresenterAdapter(TestingPresenterPort):
    """Rich interactive console presenter for testing and mutation diagnostics."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional Rich console.

        Args:
            console: Optional Rich Console instance.
        """
        self._console = console or Console()

    def present_mutation_summary(self, report: MutationAuditReport) -> int:
        """Render high-level mutation triage summary table across packages."""
        if not report.summaries:
            self._console.print(
                "[green]✨ No surviving mutants found in cache![/green]"
            )
            return 0

        table = Table(
            title="Surviving Mutants Triage Summary by Package", border_style="cyan"
        )
        table.add_column("Package", style="bold white", justify="left")
        table.add_column("Total", justify="right", style="cyan")
        table.add_column("🔴 Critical", justify="right", style="bold red")
        table.add_column("🟡 Equivalent", justify="right", style="yellow")
        table.add_column("🟢 Ignorable", justify="right", style="green")

        for s in sorted(report.summaries, key=lambda x: x.critical, reverse=True):
            crit_style = "bold red" if s.critical > 0 else "green"
            table.add_row(
                s.package_name,
                str(s.total),
                f"[{crit_style}]{s.critical}[/{crit_style}]",
                str(s.equivalent),
                str(s.ignorable),
            )

        self._console.print(table)
        if report.total_critical > 0:
            self._console.print(
                f"\n[bold red]Found {report.total_critical} critical surviving mutant(s). Run with -a to inspect.[/bold red]"
            )
            return 1
        self._console.print(
            "\n[bold green]Zero critical surviving mutants![/bold green]"
        )
        return 0

    def present_actionable_mutants(self, report: MutationAuditReport) -> int:
        """Render detailed actionable/critical mutants table."""
        if not report.actionable_mutants:
            self._console.print(
                "[green]✨ Zero actionable critical mutants found![/green]"
            )
            return 0

        table = Table(
            title="🔴 Actionable Surviving Mutants (Critical)", border_style="red"
        )
        table.add_column("ID", style="dim", width=6)
        table.add_column("File:Line", style="cyan", width=36)
        table.add_column("Mutated Code", style="bold white", width=36)
        table.add_column("Rationale", style="yellow", width=30)
        table.add_column("Covering Test(s)", style="green", width=40)

        for m in report.actionable_mutants:
            covering_str = (
                ", ".join(m.covering_tests[:2])
                if m.covering_tests
                else "[dim]Uncovered[/dim]"
            )
            if len(m.covering_tests) > 2:
                covering_str += f" (+{len(m.covering_tests) - 2} more)"
            table.add_row(
                m.id,
                f"{m.filename}:{m.line_number}",
                m.line_content[:35],
                m.rationale,
                covering_str,
            )

        self._console.print(table)
        self._console.print(
            f"\n[bold red]Total actionable mutants to address: {len(report.actionable_mutants)}[/bold red]"
        )
        return 1

    def present_boundary_audit(self, report: BoundaryAuditReport) -> int:
        """Render layer boundary leaks diagnostic table."""
        if report.is_healthy:
            self._console.print(
                Panel.fit(
                    "[bold green]✨ Zero architectural layer leaks detected in test execution contexts![/bold green]",
                    border_style="green",
                )
            )
            return 0

        table = Table(
            title="[bold red]Architectural Test Boundary Leaks[/bold red]",
            border_style="red",
        )
        table.add_column("Violating Domain Test Context", style="bold magenta")
        table.add_column("Leaked Dependency File", style="cyan")

        for leak in report.leaks:
            table.add_row(leak.test_context, leak.leaked_file)

        self._console.print(table)
        self._console.print(
            f"\n[bold red]Found {len(report.leaks)} architectural test boundary leak(s)![/bold red]"
        )
        return 1

    def present_redundancy_audit(self, report: RedundancyAuditReport) -> int:
        """Render redundant test suite table."""
        if not report.redundant_tests:
            self._console.print(
                Panel.fit(
                    "[bold green]✨ Zero redundant tests found in branch coverage![/bold green]",
                    border_style="green",
                )
            )
            return 0

        table = Table(
            title="[bold yellow]Redundant Test Contexts[/bold yellow]",
            border_style="yellow",
        )
        table.add_column("Test Context", style="bold white")

        for test in sorted(report.redundant_tests):
            table.add_row(test)

        self._console.print(table)
        self._console.print(
            f"\n[yellow]Discovered {len(report.redundant_tests)} candidate redundant test(s).[/yellow]"
        )
        return 0

    def present_impact_analysis(self, report: ImpactedTestsReport) -> int:
        """Render test impact analysis results or run status."""
        if not report.impacted_tests:
            self._console.print(
                "[green]✨ No tests impacted by modified lines.[/green]"
            )
            return 0

        self._console.print(
            Panel.fit(
                f"[bold cyan]Discovered {len(report.impacted_tests)} impacted test(s):[/bold cyan]",
                border_style="cyan",
            )
        )
        for test in sorted(report.impacted_tests):
            self._console.print(f"  [green]*[/green] {test}")

        return report.exit_code


class JsonTestingPresenterAdapter(TestingPresenterPort):
    """Machine-readable JSON presenter for test and mutation diagnostics."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize JSON presenter with optional Rich console sink.

        Args:
            console: Optional Rich Console instance.
        """
        self._console = console or Console()

    def present_mutation_summary(self, report: MutationAuditReport) -> int:
        """Serialize mutation summary to JSON."""
        payload = {
            "total_critical": report.total_critical,
            "summaries": [
                {
                    "package": s.package_name,
                    "total": s.total,
                    "critical": s.critical,
                    "equivalent": s.equivalent,
                    "ignorable": s.ignorable,
                }
                for s in report.summaries
            ],
        }
        self._console.print(json.dumps(payload, indent=2))
        return 1 if report.total_critical > 0 else 0

    def present_actionable_mutants(self, report: MutationAuditReport) -> int:
        """Serialize actionable mutants to JSON."""
        payload = {
            "total_actionable": len(report.actionable_mutants),
            "mutants": [
                {
                    "id": m.id,
                    "filename": m.filename,
                    "line_number": m.line_number,
                    "code": m.line_content,
                    "category": m.category.value,
                    "rationale": m.rationale,
                    "covering_tests": list(m.covering_tests),
                }
                for m in report.actionable_mutants
            ],
        }
        self._console.print(json.dumps(payload, indent=2))
        return 1 if report.actionable_mutants else 0

    def present_boundary_audit(self, report: BoundaryAuditReport) -> int:
        """Serialize layer boundary audit to JSON."""
        payload = {
            "status": "PASS" if report.is_healthy else "FAIL",
            "leaks_count": len(report.leaks),
            "leaks": [
                {"test_context": leak.test_context, "leaked_file": leak.leaked_file}
                for leak in report.leaks
            ],
        }
        self._console.print(json.dumps(payload, indent=2))
        return 0 if report.is_healthy else 1

    def present_redundancy_audit(self, report: RedundancyAuditReport) -> int:
        """Serialize redundancy audit to JSON."""
        payload = {
            "redundant_tests_count": len(report.redundant_tests),
            "redundant_tests": list(report.redundant_tests),
        }
        self._console.print(json.dumps(payload, indent=2))
        return 0

    def present_impact_analysis(self, report: ImpactedTestsReport) -> int:
        """Serialize test impact analysis to JSON."""
        payload = {
            "changed_files": list(report.changed_files),
            "impacted_tests_count": len(report.impacted_tests),
            "impacted_tests": list(report.impacted_tests),
            "dry_run": report.dry_run,
            "exit_code": report.exit_code,
        }
        self._console.print(json.dumps(payload, indent=2))
        return report.exit_code


class MarkdownTestingPresenterAdapter(TestingPresenterPort):
    """Markdown presenter for CI job summaries."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize Markdown presenter with optional Rich console sink.

        Args:
            console: Optional Rich Console instance.
        """
        self._console = console or Console()

    def present_mutation_summary(self, report: MutationAuditReport) -> int:
        """Render mutation summary as Markdown table."""
        lines = [
            "### Mutation Testing Triage Summary",
            "",
            "| Package | Total | Critical | Equivalent | Ignorable |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]
        for s in report.summaries:
            lines.append(
                f"| `{s.package_name}` | {s.total} | {s.critical} | {s.equivalent} | {s.ignorable} |"
            )

        lines.append(f"\n**Total Critical Mutants:** {report.total_critical}")
        self._console.print("\n".join(lines))
        return 1 if report.total_critical > 0 else 0

    def present_actionable_mutants(self, report: MutationAuditReport) -> int:
        """Render actionable mutants as Markdown table."""
        lines = [
            "### Actionable Surviving Mutants (Critical)",
            "",
            "| ID | File:Line | Code | Rationale |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for m in report.actionable_mutants:
            code_snippet = m.line_content.replace("|", "\\|").strip()
            lines.append(
                f"| `{m.id}` | `{m.filename}:{m.line_number}` | `{code_snippet}` | {m.rationale} |"
            )

        lines.append(
            f"\n**Total Actionable Mutants:** {len(report.actionable_mutants)}"
        )
        self._console.print("\n".join(lines))
        return 1 if report.actionable_mutants else 0

    def present_boundary_audit(self, report: BoundaryAuditReport) -> int:
        """Render boundary leaks as Markdown table."""
        if report.is_healthy:
            self._console.print(
                "### Architectural Test Boundaries\n\n✅ Zero layer boundary leaks detected."
            )
            return 0

        lines = [
            "### Architectural Test Boundary Leaks",
            "",
            "| Violating Test Context | Leaked File |",
            "| :--- | :--- |",
        ]
        for leak in report.leaks:
            lines.append(f"| `{leak.test_context}` | `{leak.leaked_file}` |")

        self._console.print("\n".join(lines))
        return 1

    def present_redundancy_audit(self, report: RedundancyAuditReport) -> int:
        """Render redundant tests as Markdown list."""
        lines = ["### Redundant Test Candidates", ""]
        if not report.redundant_tests:
            lines.append("✅ Zero redundant tests detected.")
        else:
            for test in report.redundant_tests:
                lines.append(f"- `{test}`")
        self._console.print("\n".join(lines))
        return 0

    def present_impact_analysis(self, report: ImpactedTestsReport) -> int:
        """Render test impact analysis as Markdown."""
        lines = [
            f"### Test Impact Analysis ({len(report.impacted_tests)} tests impacted)",
            "",
        ]
        for test in report.impacted_tests:
            lines.append(f"- `{test}`")
        self._console.print("\n".join(lines))
        return report.exit_code


def create_testing_presenter(format_name: str = "table") -> TestingPresenterPort:
    """Factory creating TestingPresenterPort implementation based on format name.

    Args:
        format_name: One of 'table', 'json', 'markdown'.

    Returns:
        TestingPresenterPort adapter instance.
    """
    fmt = format_name.lower()
    if fmt == "json":
        return JsonTestingPresenterAdapter()
    if fmt == "markdown":
        return MarkdownTestingPresenterAdapter()
    return RichTestingPresenterAdapter()
