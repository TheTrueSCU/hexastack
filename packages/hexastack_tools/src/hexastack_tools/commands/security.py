"""GitHub PR Security and Review Comments Inspector command powered by Typer."""

from __future__ import annotations

from typing import Annotated

import typer

from hexastack_tools.adapters.github import GitHubHttpAdapter
from hexastack_tools.adapters.presenters.security import present_security_comments
from hexastack_tools.domain.github import OutputFormat

app = typer.Typer(
    help="Inspect security and review comments on a GitHub PR.",
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def security(
    pr_number: Annotated[
        int,
        typer.Argument(
            help="Pull request number.",
        ),
    ],
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format: auto (detects pipes), rich (interactive tables), json (structured), plain (TSV).",
        ),
    ] = OutputFormat.AUTO,
) -> None:
    """Fetch and display review comments and security findings for a PR."""
    try:
        with GitHubHttpAdapter() as client:
            summary = client.get_pr_summary(pr_number)
            threads = summary.review_threads

        present_security_comments(threads, pr_number, output_format=output_format)
    except Exception as exc:
        typer.secho(f"Error querying PR comments: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


def main() -> None:
    """CLI entrypoint for gh-security command."""
    app()


__all__ = ["app", "main", "security"]
