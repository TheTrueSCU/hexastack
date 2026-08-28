"""Checks Presenter supporting Rich ANSI tables, structured JSON, and plain TSV."""

from __future__ import annotations

import json
import sys

from rich.console import Console
from rich.table import Table

from hexastack_tools.domain.github import CheckRunFinding, OutputFormat

console = Console()


def _render_check_conclusion(conclusion: str) -> str:
    """Format conclusion with color styling."""
    conc = conclusion.lower()
    if conc == "success":
        return "[bold green]✓ SUCCESS[/bold green]"
    if conc == "failure":
        return "[bold red]✗ FAILURE[/bold red]"
    if conc == "skipped":
        return "[dim]– SKIPPED[/dim]"
    if conc == "neutral":
        return "[dim cyan]○ NEUTRAL[/dim cyan]"
    return f"[bold yellow]⏳ {conc.upper()}[/bold yellow]"


def build_checks_table(checks: list[CheckRunFinding], ref: str) -> Table:
    """Construct Rich table for CI check runs."""
    table = Table(
        title=f"[bold cyan]GitHub CI / Check Runs for '{ref}' ({len(checks)} checks)[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Workflow", style="dim", width=22)
    table.add_column("Job / Check Name", style="bold")
    table.add_column("Status", width=12)
    table.add_column("Conclusion", width=16)
    table.add_column("Details URL", style="blue")

    for c in checks:
        table.add_row(
            c.workflow_name or "CI",
            c.name,
            c.status,
            _render_check_conclusion(c.conclusion),
            c.details_url,
        )
    return table


def render_checks_json(checks: list[CheckRunFinding], ref: str) -> str:
    """Serialize check runs to JSON."""
    data = {
        "ref": ref,
        "total_checks": len(checks),
        "checks": [
            {
                "name": c.name,
                "workflow": c.workflow_name,
                "status": c.status,
                "conclusion": c.conclusion,
                "details_url": c.details_url,
            }
            for c in checks
        ],
    }
    return json.dumps(data, indent=2)


def render_checks_plain(checks: list[CheckRunFinding], ref: str) -> str:
    """Serialize check runs to plain TSV lines."""
    lines = [f"REF\t{ref}\t{len(checks)}"]
    for c in checks:
        lines.append(
            f"CHECK\t{c.workflow_name or 'CI'}\t{c.name}\t{c.status}\t{c.conclusion}\t{c.details_url}"
        )
    return "\n".join(lines)


def present_checks(
    checks: list[CheckRunFinding],
    ref: str,
    output_format: OutputFormat = OutputFormat.RICH,
) -> None:
    """Unified entrypoint to present CI check runs in rich, json, or plain format."""
    if output_format == OutputFormat.JSON:
        sys.stdout.write(render_checks_json(checks, ref) + "\n")
        sys.stdout.flush()
    elif output_format == OutputFormat.PLAIN:
        sys.stdout.write(render_checks_plain(checks, ref) + "\n")
        sys.stdout.flush()
    else:
        console.print(build_checks_table(checks, ref))


__all__ = [
    "build_checks_table",
    "present_checks",
    "render_checks_json",
    "render_checks_plain",
]
