"""PR Summary Presenter supporting Rich ANSI panels, structured JSON, and plain TSV."""

from __future__ import annotations

import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.domain.github import (
    CheckRunFinding,
    OutputFormat,
    PRSummary,
    ReviewThread,
)

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


def _build_checks_table(check_runs: tuple[CheckRunFinding, ...]) -> Table:
    """Construct Rich table for CI check runs."""
    table = Table(
        title=f"[bold cyan]CI / Check Runs ({len(check_runs)} checks)[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Workflow", style="dim", width=22)
    table.add_column("Job / Check Name", style="bold")
    table.add_column("Status", width=12)
    table.add_column("Conclusion", width=16)
    table.add_column("Details URL", style="blue")

    for c in check_runs:
        table.add_row(
            c.workflow_name or "CI",
            c.name,
            c.status,
            _render_check_conclusion(c.conclusion),
            c.details_url,
        )
    return table


def _build_threads_table(threads: tuple[ReviewThread, ...]) -> Table:
    """Construct Rich table for PR review conversation threads."""
    table = Table(
        title=f"[bold cyan]Review & Conversation Threads ({len(threads)} threads)[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Thread ID", style="dim", width=12)
    table.add_column("Author", style="bold", width=20)
    table.add_column("Location", style="cyan", width=30)
    table.add_column("Status", width=14)
    table.add_column("Latest Snippet")

    for t in threads:
        if not t.comments:
            continue
        first_c = t.comments[0]
        author = first_c.author
        loc = f"{first_c.path}:{first_c.line}" if first_c.path else "Discussion"
        snippet = first_c.body.strip().split("\n")[0][:80]

        if "bot" in author.lower() or "security" in author.lower():
            author_styled = f"[yellow]🤖 {author}[/yellow]"
        else:
            author_styled = f"[cyan]{author}[/cyan]"

        status_styled = (
            "[bold green]✓ Resolved[/bold green]"
            if t.is_resolved
            else "[bold red]✗ Unresolved[/bold red]"
        )
        table.add_row(t.id, author_styled, loc, status_styled, snippet)
    return table


def render_pr_summary_rich(summary: PRSummary, show_details: bool = False) -> None:
    """Render full PR inspection dashboard using Rich components."""
    state_style = "bold green" if summary.state == "open" else "bold purple"
    clean_badge = (
        "[bold green]✓ CLEAN (Ready for Merge)[/bold green]"
        if summary.is_clean
        else "[bold red]✗ BLOCKED (Has Failures/Unresolved Threads)[/bold red]"
    )

    header_body = (
        f"[bold white]Title:[/bold white] {summary.title}\n"
        f"[bold white]Author:[/bold white] [cyan]@{summary.author}[/cyan]\n"
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
                "workflow": c.workflow_name,
                "details_url": c.details_url,
            }
            for c in summary.check_runs
        ],
        "review_threads": [
            {
                "id": t.id,
                "is_resolved": t.is_resolved,
                "resolved_by": t.resolved_by,
                "comments": [
                    {
                        "id": c.id,
                        "author": c.author,
                        "body": c.body,
                        "path": c.path,
                        "line": c.line,
                        "created_at": c.created_at,
                    }
                    for c in t.comments
                ],
            }
            for t in summary.review_threads
        ],
    }
    return json.dumps(data, indent=2)


def render_pr_summary_plain(summary: PRSummary) -> str:
    """Serialize PRSummary to line-delimited TSV string."""
    lines: list[str] = [
        f"PR\t{summary.number}\t{summary.state}\t{summary.mergeable}\t{summary.head_ref}\t{summary.base_ref}\t{summary.html_url}"
    ]
    for c in summary.check_runs:
        lines.append(
            f"CHECK\t{c.workflow_name or 'CI'}\t{c.name}\t{c.status}\t{c.conclusion}\t{c.details_url}"
        )

    for t in summary.review_threads:
        status = "RESOLVED" if t.is_resolved else "UNRESOLVED"
        for c in t.comments:
            lines.append(
                f"THREAD\t{t.id}\t{status}\t{c.author}\t{c.path or '-'}:{c.line or '-'}\t{c.body.strip().splitlines()[0]}"
            )
    return "\n".join(lines)


def present_pr_summary(
    summary: PRSummary,
    output_format: OutputFormat = OutputFormat.RICH,
    show_details: bool = False,
) -> None:
    """Unified entrypoint to present PR summary in rich, json, or plain format."""
    if output_format == OutputFormat.JSON:
        sys.stdout.write(render_pr_summary_json(summary) + "\n")
        sys.stdout.flush()
    elif output_format == OutputFormat.PLAIN:
        sys.stdout.write(render_pr_summary_plain(summary) + "\n")
        sys.stdout.flush()
    else:
        render_pr_summary_rich(summary, show_details=show_details)


__all__ = [
    "present_pr_summary",
    "render_pr_summary_json",
    "render_pr_summary_plain",
    "render_pr_summary_rich",
]
