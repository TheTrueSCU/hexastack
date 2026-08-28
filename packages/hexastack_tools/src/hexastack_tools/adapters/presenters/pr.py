"""Rich and JSON Presenters for PR examination and status auditing."""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.domain.github import (
    CheckRunFinding,
    PRSummary,
    ReviewThread,
)

console = Console()


def _render_check_conclusion(conclusion: str) -> str:
    """Format check conclusion badge with rich styling."""
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


def _build_checks_table(checks: tuple[CheckRunFinding, ...]) -> Table:
    """Build formatted table of CI check runs."""
    check_table = Table(
        title=f"[bold cyan]CI & Check Runs ({len(checks)} checks)[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    check_table.add_column("Workflow", style="dim", width=22)
    check_table.add_column("Job / Check Name", style="bold")
    check_table.add_column("Status", width=12)
    check_table.add_column("Conclusion", width=16)
    check_table.add_column("Log Details", style="blue")

    for c in checks:
        check_table.add_row(
            c.workflow_name or "CI",
            c.name,
            c.status,
            _render_check_conclusion(c.conclusion),
            c.details_url,
        )
    return check_table


def _build_threads_table(threads: tuple[ReviewThread, ...]) -> Table:
    """Build formatted table of review discussion threads."""
    thread_table = Table(
        title=f"[bold cyan]Review Conversations & Security Audit ({len(threads)} threads)[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    thread_table.add_column("Thread ID", style="dim", width=14)
    thread_table.add_column("Author", style="bold", width=24)
    thread_table.add_column("File / Location", width=36)
    thread_table.add_column("Resolution Status", width=20)
    thread_table.add_column("Snippet / Comment")

    for t in threads:
        first_c = t.comments[0] if t.comments else None
        author = first_c.author if first_c else "unknown"
        loc = f"{first_c.path}:{first_c.line}" if first_c and first_c.path else "-"
        snippet = first_c.body.splitlines()[0][:60] if first_c else ""

        if t.is_resolved:
            res_styled = (
                f"[bold green]✓ RESOLVED[/bold green] (by @{t.resolved_by or 'bot'})"
            )
        else:
            res_styled = "[bold red]✗ UNRESOLVED[/bold red]"

        thread_table.add_row(
            t.id[-8:],
            author,
            loc,
            res_styled,
            snippet,
        )
    return thread_table


def render_pr_summary_rich(summary: PRSummary, show_details: bool = False) -> None:
    """Render a comprehensive Rich dashboard for PRSummary."""
    state_style = "bold green" if summary.state == "open" else "bold purple"
    clean_badge = (
        "[bold green]✓ READY TO MERGE[/bold green]"
        if summary.is_clean
        else "[bold red]✗ CHECKS / REVIEWS REQUIRED[/bold red]"
    )

    header_body = (
        f"[bold white]Title:[/bold white] {summary.title}\n"
        f"[bold white]Author:[/bold white] @{summary.author}\n"
        f"[bold white]Branch:[/bold white] [bold cyan]{summary.head_ref}[/bold cyan] ➔ [bold cyan]{summary.base_ref}[/bold cyan]\n"
        f"[bold white]State:[/bold white] [{state_style}]{summary.state.upper()}[/{state_style}] (mergeable: [bold]{summary.mergeable}[/bold])\n"
        f"[bold white]URL:[/bold white] [blue]{summary.html_url}[/blue]\n"
        f"[bold white]Status:[/bold white] {clean_badge}"
    )
    console.print(
        Panel(
            header_body,
            title=f"[bold magenta]Pull Request #{summary.number} Overview[/bold magenta]",
            border_style="magenta",
        )
    )

    if summary.check_runs:
        console.print(_build_checks_table(summary.check_runs))

    if summary.review_threads:
        console.print(_build_threads_table(summary.review_threads))

    if show_details:
        for t in summary.review_threads:
            if not t.is_resolved and t.comments:
                for c in t.comments:
                    console.print(
                        Panel(
                            f"[bold white]Location:[/bold white] {c.path}:{c.line}\n\n{c.body}",
                            title=f"[bold red]Unresolved Review: @{c.author}[/bold red]",
                            border_style="red",
                        )
                    )


def render_pr_summary_json(summary: PRSummary) -> str:
    """Serialize PRSummary to formatted JSON string."""
    data = {
        "number": summary.number,
        "title": summary.title,
        "author": summary.author,
        "state": summary.state,
        "mergeable": summary.mergeable,
        "is_draft": summary.is_draft,
        "head_ref": summary.head_ref,
        "base_ref": summary.base_ref,
        "html_url": summary.html_url,
        "is_clean": summary.is_clean,
        "check_runs": [
            {
                "name": c.name,
                "status": c.status,
                "conclusion": c.conclusion,
                "details_url": c.details_url,
                "workflow_name": c.workflow_name,
            }
            for c in summary.check_runs
        ],
        "review_threads": [
            {
                "id": t.id,
                "is_resolved": t.is_resolved,
                "resolved_by": t.resolved_by,
                "comments_count": len(t.comments),
            }
            for t in summary.review_threads
        ],
    }
    return json.dumps(data, indent=2)


__all__ = [
    "render_pr_summary_json",
    "render_pr_summary_rich",
]
