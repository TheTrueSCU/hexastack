"""GitHub PR Check status auditor and CLI inspector.

Notes/Architectural Intent:
    Retrieves and displays PR checks and commit statuses with Rich table formatting,
    identifying failed, pending, and skipped jobs directly via HTTP.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from rich.console import Console
from rich.table import Table

from scripts.github._client import GitHubClient

__all__ = [
    "format_checks_table",
    "inspect_checks",
    "main",
]

console = Console()


def format_checks_table(checks_data: dict[str, Any], ref: str) -> Table:
    """Render check runs and commit statuses into a Rich table.

    Args:
        checks_data: Dictionary containing 'check_runs' and 'statuses'.
        ref: Target Git ref or PR branch.

    Returns:
        Formatted Rich Table object.
    """
    table = Table(
        title=f"[bold cyan]GitHub CI / Check Runs for '{ref}'[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Type", style="dim", width=12)
    table.add_column("Name", style="bold")
    table.add_column("Status", width=12)
    table.add_column("Conclusion / State", width=18)
    table.add_column("Details URL", style="blue")

    for run in checks_data.get("check_runs", []):
        name = run.get("name", "unknown")
        status = run.get("status", "unknown")
        conclusion = run.get("conclusion") or "in_progress"
        url = run.get("html_url", "")

        if conclusion == "success":
            conc_styled = "[bold green]✓ success[/bold green]"
        elif conclusion == "failure":
            conc_styled = "[bold red]✗ failure[/bold red]"
        elif conclusion == "skipped":
            conc_styled = "[dim]– skipped[/dim]"
        elif conclusion == "cancelled":
            conc_styled = "[yellow]⚠ cancelled[/yellow]"
        else:
            conc_styled = f"[cyan]{conclusion}[/cyan]"

        table.add_row("Check Run", name, status, conc_styled, url)

    for st in checks_data.get("statuses", []):
        context = st.get("context", "status")
        state = st.get("state", "unknown")
        url = st.get("target_url", "")

        if state == "success":
            state_styled = "[bold green]✓ success[/bold green]"
        elif state in ("failure", "error"):
            state_styled = f"[bold red]✗ {state}[/bold red]"
        elif state == "pending":
            state_styled = "[yellow]⣾ pending[/yellow]"
        else:
            state_styled = state

        table.add_row("Status", context, "completed", state_styled, url)

    return table


def inspect_checks(ref_or_pr: str) -> int:
    """Inspect CI status checks for a given PR number or Git ref.

    Args:
        ref_or_pr: PR number string or Git branch/commit SHA.

    Returns:
        0 if all checks succeeded or are in progress, 1 if any failure detected.
    """
    with GitHubClient() as client:
        ref = ref_or_pr
        if ref_or_pr.isdigit():
            pr = client.get_pr(int(ref_or_pr))
            ref = pr.get("head", {}).get("sha", ref_or_pr)

        data = client.list_pr_checks(ref)
        table = format_checks_table(data, ref_or_pr)
        console.print(table)

        has_failure = any(
            run.get("conclusion") == "failure" for run in data.get("check_runs", [])
        ) or any(
            st.get("state") in ("failure", "error") for st in data.get("statuses", [])
        )
        return 1 if has_failure else 0


def main() -> int:
    """CLI entrypoint for gh-checks script."""
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
