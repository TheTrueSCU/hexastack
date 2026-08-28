"""GitHub PR check auditor command."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from rich.console import Console
from rich.table import Table

from hexastack_tools.adapters.github import GitHubHttpAdapter

console = Console()


def format_checks_table(checks: list[Any], ref: str) -> Table:
    """Render check runs into a Rich table."""
    table = Table(
        title=f"[bold cyan]GitHub CI / Check Runs for '{ref}'[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Workflow", style="dim", width=22)
    table.add_column("Job / Check Name", style="bold")
    table.add_column("Status", width=12)
    table.add_column("Conclusion", width=16)
    table.add_column("Details URL", style="blue")

    for c in checks:
        conc = c.conclusion.lower()
        if conc == "success":
            conc_styled = "[bold green]✓ SUCCESS[/bold green]"
        elif conc == "failure":
            conc_styled = "[bold red]✗ FAILURE[/bold red]"
        elif conc == "skipped":
            conc_styled = "[dim]– SKIPPED[/dim]"
        elif conc == "neutral":
            conc_styled = "[dim cyan]○ NEUTRAL[/dim cyan]"
        else:
            conc_styled = f"[bold yellow]⏳ {conc.upper()}[/bold yellow]"

        table.add_row(
            c.workflow_name or "CI",
            c.name,
            c.status,
            conc_styled,
            c.details_url,
        )
    return table


def inspect_checks(ref_or_pr: str) -> int:
    """Inspect CI status checks for a given PR number or Git ref."""
    with GitHubHttpAdapter() as client:
        ref = ref_or_pr
        if ref_or_pr.isdigit():
            summary = client.get_pr_summary(int(ref_or_pr))
            checks = list(summary.check_runs)
        else:
            checks = client.get_check_runs(ref)

        table = format_checks_table(checks, ref_or_pr)
        console.print(table)

        has_failure = any(c.conclusion.lower() == "failure" for c in checks)
        return 1 if has_failure else 0


def main() -> int:
    """CLI entrypoint for gh-checks command."""
    parser = argparse.ArgumentParser(description="Inspect GitHub CI and status checks.")
    parser.add_argument("ref", help="Pull request number or commit ref/branch name.")
    args = parser.parse_args()

    try:
        return inspect_checks(args.ref)
    except Exception as exc:
        console.print(f"[bold red]Error querying GitHub checks:[/bold red] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
