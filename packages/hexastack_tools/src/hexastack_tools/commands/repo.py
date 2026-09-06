"""GitHub repository configuration and governance inspection command powered by Typer and Presenters."""

from __future__ import annotations

from typing import Annotated

import typer

from hexastack_tools.adapters.github import GitHubHttpAdapter
from hexastack_tools.adapters.presenters.repo import present_repo_status
from hexastack_tools.domain.github import OutputFormat

app = typer.Typer(
    help="Inspect GitHub repository configuration, actions permissions, and environments.",
    add_completion=False,
    no_args_is_help=False,
)


@app.command()
def repo_status(
    repo_name: Annotated[
        str | None,
        typer.Argument(
            help="Optional repository in 'owner/repo' or 'repo' format (defaults to TheTrueSCU/hexastack).",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format: auto (detects pipes), rich (interactive tables), json (structured), plain (TSV).",
        ),
    ] = OutputFormat.AUTO,
) -> None:
    """Inspect repository configuration, Actions permissions, and environments."""
    owner: str | None = None
    target_repo: str | None = None

    if repo_name:
        if "/" in repo_name:
            owner, target_repo = repo_name.split("/", 1)
        else:
            target_repo = repo_name

    try:
        with GitHubHttpAdapter(owner=owner, repo=target_repo) as client:
            status = client.get_repo_status(owner=owner, repo=target_repo)

        present_repo_status(status, output_format=output_format)
    except Exception as exc:
        typer.secho(
            f"Error querying GitHub repository status: {exc}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1) from exc


def main() -> None:
    """CLI entrypoint for gh-repo command."""
    app()


__all__ = ["app", "main", "repo_status"]
