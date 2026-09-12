"""Dependency and architecture boundary presenters supporting Rich, JSON, and Markdown formats.

Notes/Architectural Intent:
    Decouples packaging extras, import boundaries, and unified dependency health reporting
    from terminal presentation, enabling human interactive use, CI summaries, and machine consumption.
"""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.domain.dependencies import (
    DeptryAuditReport,
    ExtrasAuditResult,
    ImportLinterReport,
    UnifiedDependencyAuditReport,
)
from hexastack_tools.ports.dependencies import DependencyPresenterPort

__all__ = [
    "create_dependency_presenter",
    "JsonDependencyPresenterAdapter",
    "MarkdownDependencyPresenterAdapter",
    "RichDependencyPresenterAdapter",
]


class RichDependencyPresenterAdapter(DependencyPresenterPort):
    """Rich console presenter implementing DependencyPresenterPort."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize presenter with optional Rich console.

        Args:
            console: Optional Rich Console instance.
        """
        self._console = console or Console()

    def present_extras_parity(
        self,
        result: ExtrasAuditResult,
        diagram: str | None = None,
    ) -> int:
        """Render extras parity audit or Mermaid diagram with Rich tables and panels."""
        if diagram is not None:
            self._console.print(diagram)
            return 0

        if result.is_healthy:
            self._console.print(
                "[bold green]✓ All subpackage optional extras are properly forwarded in the umbrella package.[/bold green]"
            )
            return 0

        table = Table(
            title="[bold red]❌ Optional Extras Parity Violations[/bold red]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Subpackage", style="bold cyan", width=22)
        table.add_column("Extra", style="yellow", width=16)
        table.add_column("Dependencies", width=30)
        table.add_column("Suggested Fix", style="green")

        for v in result.violations:
            deps_preview = ", ".join(v.dependencies[:2])
            if len(v.dependencies) > 2:
                deps_preview += f" (+{len(v.dependencies) - 2} more)"
            table.add_row(
                v.subpackage, f"[{v.extra_name}]", deps_preview, v.suggested_fix
            )

        self._console.print(table)
        self._console.print(
            f"\n[bold red]Found {len(result.violations)} subpackage extra(s) missing from umbrella packaging.[/bold red]"
        )
        return 1

    def present_deptry_audit(self, report: DeptryAuditReport) -> int:
        """Render deptry dependency auditor table."""
        table = Table(
            title="[bold cyan]Deptry Workspace Dependency Auditor[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Package", style="bold")
        table.add_column("Status", width=12)
        table.add_column("Details")

        for r in report.results:
            if r.passed:
                table.add_row(r.package_name, "[bold green]PASSED[/bold green]", "")
            else:
                table.add_row(
                    r.package_name, "[bold red]FAILED[/bold red]", r.error_output
                )

        self._console.print(table)
        if report.exit_code != 0:
            self._console.print(
                Panel(
                    "[bold red]❌ Deptry detected undeclared or missing dependencies.[/bold red]",
                    border_style="red",
                )
            )
        else:
            self._console.print(
                Panel(
                    "[bold green]✨ All package dependencies explicitly declared in pyproject.toml.[/bold green]",
                    border_style="green",
                )
            )
        return report.exit_code

    def present_import_linter(self, report: ImportLinterReport) -> int:
        """Render hexagonal architecture layer contract table."""
        table = Table(
            title="[bold cyan]Hexagonal Architecture Layer Contracts[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Package", style="bold")
        table.add_column("Status", width=12)
        table.add_column("Details")

        for r in report.results:
            if r.passed:
                table.add_row(r.package_name, "[bold green]PASSED[/bold green]", "")
            else:
                table.add_row(
                    r.package_name, "[bold red]FAILED[/bold red]", r.error_output
                )

        self._console.print(table)
        return report.exit_code

    def present_unified_deps_audit(
        self,
        report: UnifiedDependencyAuditReport,
    ) -> int:
        """Render unified dependency audit dashboard table and error list."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Audit Check", style="bold", width=36)
        table.add_column("Status", width=12)

        for item in report.items:
            status = (
                "[green]✅ Passed[/green]" if item.passed else "[red]❌ Failed[/red]"
            )
            table.add_row(item.check_name, status)

        self._console.print(table)

        if report.is_healthy:
            self._console.print(
                "\n[bold green]🎉 All dependencies, optional extras, and packaging contracts are 100% healthy![/bold green]"
            )
            return 0

        self._console.print("\n[bold red]❌ Found dependency issues:[/bold red]")
        for err in report.errors:
            self._console.print(f"  • {err}")
        return 1


class JsonDependencyPresenterAdapter(DependencyPresenterPort):
    """Machine-readable JSON presenter for dependency outputs."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize JSON presenter with optional Console sink."""
        self._console = console or Console()

    def present_extras_parity(
        self,
        result: ExtrasAuditResult,
        diagram: str | None = None,
    ) -> int:
        """Serialize extras parity audit to JSON."""
        if diagram is not None:
            self._console.print(json.dumps({"diagram": diagram}, indent=2))
            return 0

        payload = {
            "status": "PASS" if result.is_healthy else "FAIL",
            "total_packages_checked": result.total_packages_checked,
            "violations_count": len(result.violations),
            "violations": [
                {
                    "subpackage": v.subpackage,
                    "extra_name": v.extra_name,
                    "dependencies": list(v.dependencies),
                    "suggested_fix": v.suggested_fix,
                }
                for v in result.violations
            ],
        }
        self._console.print(json.dumps(payload, indent=2))
        return 0 if result.is_healthy else 1

    def present_deptry_audit(self, report: DeptryAuditReport) -> int:
        """Serialize deptry audit to JSON."""
        payload = {
            "status": "PASS" if report.exit_code == 0 else "FAIL",
            "exit_code": report.exit_code,
            "results": [
                {
                    "package": r.package_name,
                    "passed": r.passed,
                    "error_output": r.error_output or None,
                }
                for r in report.results
            ],
        }
        self._console.print(json.dumps(payload, indent=2))
        return report.exit_code

    def present_import_linter(self, report: ImportLinterReport) -> int:
        """Serialize import-linter contract results to JSON."""
        payload = {
            "status": "PASS" if report.exit_code == 0 else "FAIL",
            "exit_code": report.exit_code,
            "results": [
                {
                    "package": r.package_name,
                    "passed": r.passed,
                    "error_output": r.error_output or None,
                }
                for r in report.results
            ],
        }
        self._console.print(json.dumps(payload, indent=2))
        return report.exit_code

    def present_unified_deps_audit(
        self,
        report: UnifiedDependencyAuditReport,
    ) -> int:
        """Serialize unified dependency report to JSON."""
        payload = {
            "status": "PASS" if report.is_healthy else "FAIL",
            "is_healthy": report.is_healthy,
            "diagram_generated": report.diagram_generated,
            "items": [
                {
                    "check": item.check_name,
                    "passed": item.passed,
                    "details": item.details,
                }
                for item in report.items
            ],
            "errors": list(report.errors),
        }
        self._console.print(json.dumps(payload, indent=2))
        return 0 if report.is_healthy else 1


class MarkdownDependencyPresenterAdapter(DependencyPresenterPort):
    """GitHub-flavored Markdown presenter for CI summaries and pull requests."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize Markdown presenter with optional Console sink."""
        self._console = console or Console()

    def present_extras_parity(
        self,
        result: ExtrasAuditResult,
        diagram: str | None = None,
    ) -> int:
        """Render extras parity audit or Mermaid diagram as Markdown."""
        if diagram is not None:
            self._console.print(diagram)
            return 0

        if result.is_healthy:
            self._console.print(
                "> ✅ **All subpackage optional extras are properly forwarded in the umbrella package.**"
            )
            return 0

        lines: list[str] = [
            "### ❌ Optional Extras Parity Violations",
            "",
            "| Subpackage | Extra | Dependencies | Suggested Fix |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for v in result.violations:
            deps_preview = ", ".join(v.dependencies[:2])
            if len(v.dependencies) > 2:
                deps_preview += f" (+{len(v.dependencies) - 2} more)"
            lines.append(
                f"| `{v.subpackage}` | `[{v.extra_name}]` | `{deps_preview}` | {v.suggested_fix} |"
            )

        self._console.print("\n".join(lines))
        return 1

    def present_deptry_audit(self, report: DeptryAuditReport) -> int:
        """Render deptry audit as Markdown table."""
        lines: list[str] = [
            "### Deptry Workspace Dependency Auditor",
            "",
            "| Package | Status | Details |",
            "| :--- | :---: | :--- |",
        ]
        for r in report.results:
            icon = "✅ PASSED" if r.passed else "❌ FAILED"
            details = f"`{r.error_output}`" if r.error_output else ""
            lines.append(f"| `{r.package_name}` | {icon} | {details} |")

        self._console.print("\n".join(lines))
        return report.exit_code

    def present_import_linter(self, report: ImportLinterReport) -> int:
        """Render hexagonal architecture layer contracts as Markdown."""
        lines: list[str] = [
            "### Hexagonal Architecture Layer Contracts",
            "",
            "| Package | Status | Details |",
            "| :--- | :---: | :--- |",
        ]
        for r in report.results:
            icon = "✅ PASSED" if r.passed else "❌ FAILED"
            details = f"`{r.error_output}`" if r.error_output else ""
            lines.append(f"| `{r.package_name}` | {icon} | {details} |")

        self._console.print("\n".join(lines))
        return report.exit_code

    def present_unified_deps_audit(
        self,
        report: UnifiedDependencyAuditReport,
    ) -> int:
        """Render unified dependency audit dashboard as Markdown."""
        lines: list[str] = [
            "### Hexastack Unified Dependency & Packaging Auditor",
            "",
            "| Audit Check | Status |",
            "| :--- | :---: |",
        ]
        for item in report.items:
            status = "✅ Passed" if item.passed else "❌ Failed"
            lines.append(f"| {item.check_name} | {status} |")

        if report.is_healthy:
            lines.append("")
            lines.append(
                "> 🎉 **All dependencies, optional extras, and packaging contracts are 100% healthy!**"
            )
        else:
            lines.append("")
            lines.append("### ❌ Dependency Issues Found")
            for err in report.errors:
                lines.append(f"- {err}")

        self._console.print("\n".join(lines))
        return 0 if report.is_healthy else 1


def create_dependency_presenter(
    format_type: str = "table",
    console: Console | None = None,
) -> DependencyPresenterPort:
    """Factory creating DependencyPresenterPort instance for desired output format.

    Args:
        format_type: Output format name ('table', 'json', 'markdown').
        console: Optional Console instance.

    Returns:
        Configured DependencyPresenterPort adapter.

    Raises:
        ValueError: If format_type is not supported.
    """
    fmt = format_type.strip().lower()
    if fmt == "table":
        return RichDependencyPresenterAdapter(console=console)
    if fmt == "json":
        return JsonDependencyPresenterAdapter(console=console)
    if fmt in ("markdown", "md"):
        return MarkdownDependencyPresenterAdapter(console=console)

    raise ValueError(
        f"Unsupported dependency presenter format: {format_type!r}. Supported formats: 'table', 'json', 'markdown'."
    )
