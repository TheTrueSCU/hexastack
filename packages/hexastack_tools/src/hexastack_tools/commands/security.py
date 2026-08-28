"""GitHub PR Security and Review Comments Inspector command."""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.adapters.github import GitHubHttpAdapter

console = Console()


def inspect_security_comments(pr_number: int) -> int:
    """Fetch and display review comments and security findings for a PR."""
    with GitHubHttpAdapter() as client:
        summary = client.get_pr_summary(pr_number)
        threads = summary.review_threads

    if not threads:
        console.print(
            Panel(
                f"[bold green]No inline security or review comments found on PR #{pr_number}.[/bold green]",
                title="[bold cyan]PR Security Review[/bold cyan]",
            )
        )
        return 0

    table = Table(
        title=f"[bold cyan]Review & Security Comments on PR #{pr_number}[/bold cyan]",
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

    console.print(table)
    return 0


def main() -> int:
    """CLI entrypoint for gh-security command."""
    parser = argparse.ArgumentParser(
        description="Inspect security and review comments on a GitHub PR."
    )
    parser.add_argument("pr", type=int, help="Pull request number.")
    args = parser.parse_args()

    try:
        return inspect_security_comments(args.pr)
    except Exception as exc:
        console.print(f"[bold red]Error querying PR comments:[/bold red] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
