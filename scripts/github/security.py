"""GitHub Security and Automated Review Comment Inspector.

Notes/Architectural Intent:
    Fetches and filters PR review comments and automated security findings (CodeQL,
    Codecov, OpenSSF) with Rich formatted tables.
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts.github._client import GitHubClient

__all__ = [
    "inspect_security_comments",
    "main",
]

console = Console()


def inspect_security_comments(pr_number: int) -> int:
    """Fetch and display review comments and security findings for a PR.

    Args:
        pr_number: Target Pull Request number.

    Returns:
        0 if clean or comments displayed, 1 on error.
    """
    with GitHubClient() as client:
        comments = client.list_pr_comments(pr_number)

    if not comments:
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
    table.add_column("Comment Snippet")

    for c in comments:
        author = c.get("user", {}).get("login", "unknown")
        path = c.get("path", "")
        line = str(c.get("line") or c.get("original_line") or "-")
        body = c.get("body", "").strip().split("\n")[0][:100]

        if "bot" in author.lower() or "security" in author.lower():
            author_styled = f"[yellow]🤖 {author}[/yellow]"
        else:
            author_styled = f"[cyan]{author}[/cyan]"

        table.add_row(author_styled, path, line, body)

    console.print(table)
    return 0


def main() -> int:
    """CLI entrypoint for gh-security script."""
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
