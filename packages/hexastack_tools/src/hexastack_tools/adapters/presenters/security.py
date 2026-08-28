"""Security Presenter supporting Rich ANSI tables, structured JSON, and plain TSV."""

from __future__ import annotations

import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.adapters.presenters.common import resolve_output_format
from hexastack_tools.domain.github import OutputFormat, ReviewThread

console = Console()


def build_security_comments_table(
    threads: tuple[ReviewThread, ...], pr_number: int
) -> Table:
    """Construct Rich table for PR review and security comments."""
    table = Table(
        title=f"[bold cyan]Review & Security Comments on PR #{pr_number} ({len(threads)} threads)[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Author", style="bold", width=25)
    table.add_column("File Path", style="dim")
    table.add_column("Line", width=6)
    table.add_column("Status", width=14)
    table.add_column("Comment Snippet")

    for t in threads:
        for c in t.comments:
            author = c.author
            path = c.path or ""
            line = str(c.line or "-")
            body = c.body.strip().split("\n")[0][:100]

            if "bot" in author.lower() or "security" in author.lower():
                author_styled = f"[yellow]🤖 {author}[/yellow]"
            else:
                author_styled = f"[cyan]{author}[/cyan]"

            status_styled = (
                "[bold green]✓ Resolved[/bold green]"
                if t.is_resolved
                else "[bold red]✗ Unresolved[/bold red]"
            )
            table.add_row(author_styled, path, line, status_styled, body)

    return table


def render_security_comments_json(
    threads: tuple[ReviewThread, ...], pr_number: int
) -> str:
    """Serialize review threads to JSON."""
    data = {
        "pr_number": pr_number,
        "threads_count": len(threads),
        "threads": [
            {
                "id": t.id,
                "is_resolved": t.is_resolved,
                "resolved_by": t.resolved_by,
                "comments": [
                    {
                        "author": c.author,
                        "path": c.path,
                        "line": c.line,
                        "body": c.body,
                        "created_at": c.created_at,
                    }
                    for c in t.comments
                ],
            }
            for t in threads
        ],
    }
    return json.dumps(data, indent=2)


def render_security_comments_plain(
    threads: tuple[ReviewThread, ...], pr_number: int
) -> str:
    """Serialize review threads to plain TSV lines."""
    lines = [f"PR\t{pr_number}\t{len(threads)}"]
    for t in threads:
        status = "RESOLVED" if t.is_resolved else "UNRESOLVED"
        for c in t.comments:
            lines.append(
                f"THREAD\t{t.id}\t{status}\t{c.author}\t{c.path or '-'}:{c.line or '-'}\t{c.body.strip().splitlines()[0]}"
            )
    return "\n".join(lines)


def present_security_comments(
    threads: tuple[ReviewThread, ...],
    pr_number: int,
    output_format: OutputFormat = OutputFormat.AUTO,
) -> None:
    """Unified entrypoint to present security/review comments in rich, json, plain, or auto-detected format."""
    resolved_format = resolve_output_format(output_format)
    if not threads and resolved_format == OutputFormat.RICH:
        console.print(
            Panel(
                f"[bold green]No inline security or review comments found on PR #{pr_number}.[/bold green]",
                title="[bold cyan]PR Security Review[/bold cyan]",
            )
        )
        return

    if resolved_format == OutputFormat.JSON:
        sys.stdout.write(render_security_comments_json(threads, pr_number) + "\n")
        sys.stdout.flush()
    elif resolved_format == OutputFormat.PLAIN:
        sys.stdout.write(render_security_comments_plain(threads, pr_number) + "\n")
        sys.stdout.flush()
    else:
        console.print(build_security_comments_table(threads, pr_number))


__all__ = [
    "build_security_comments_table",
    "present_security_comments",
    "render_security_comments_json",
    "render_security_comments_plain",
]
