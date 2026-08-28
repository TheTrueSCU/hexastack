"""Single-step PR Examination and Verification Tool powered by Typer and Presenters."""

from __future__ import annotations

import json
import subprocess
import time
from typing import Annotated

import typer
from rich.console import Console

from hexastack_tools.adapters.github import GitHubHttpAdapter
from hexastack_tools.adapters.presenters.pr import present_pr_summary
from hexastack_tools.domain.github import OutputFormat

console = Console()

app = typer.Typer(
    help="Examine a Pull Request's complete health dashboard.",
    add_completion=False,
)


def discover_current_pr() -> int:
    """Auto-discover the open PR associated with current git branch using `gh` CLI."""
    try:
        res = subprocess.run(
            ["gh", "pr", "view", "--json", "number"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(res.stdout)
        pr_number = data.get("number")
        if isinstance(pr_number, int):
            return pr_number
    except Exception as exc:
        raise RuntimeError(
            "Could not auto-discover PR for current branch. Specify PR number."
        ) from exc
    raise RuntimeError("Could not determine PR number from gh CLI output.")


def examine_pr(
    pr_number: int | None,
    output_format: OutputFormat = OutputFormat.RICH,
    show_details: bool = False,
    watch: bool = False,
    poll_interval: int = 15,
) -> int:
    """Fetch and render PR status."""
    target_pr = pr_number if pr_number is not None else discover_current_pr()

    with GitHubHttpAdapter() as client:
        while True:
            summary = client.get_pr_summary(target_pr)
            if output_format == OutputFormat.RICH and watch:
                console.clear()

            present_pr_summary(
                summary, output_format=output_format, show_details=show_details
            )

            if not watch:
                return 0 if summary.is_clean else 1

            time.sleep(poll_interval)


@app.command()
def examine(
    pr_number: Annotated[
        int | None,
        typer.Argument(
            help="Pull request number (defaults to current branch PR).",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format: rich (interactive panels), json (structured), plain (TSV).",
        ),
    ] = OutputFormat.RICH,
    show_details: Annotated[
        bool,
        typer.Option(
            "--details",
            "-d",
            help="Display full review comment discussions.",
        ),
    ] = False,
    watch: Annotated[
        bool,
        typer.Option(
            "--watch",
            "-w",
            help="Continuously poll and refresh until all checks and reviews resolve.",
        ),
    ] = False,
    interval: Annotated[
        int,
        typer.Option(
            "--interval",
            "-i",
            help="Polling interval in seconds when watching.",
        ),
    ] = 15,
) -> None:
    """Examine a Pull Request's complete health status."""
    try:
        code = examine_pr(
            pr_number=pr_number,
            output_format=output_format,
            show_details=show_details,
            watch=watch,
            poll_interval=interval,
        )
        if code != 0:
            raise typer.Exit(code=code)
    except typer.Exit:
        raise
    except Exception as exc:
        typer.secho(f"Error examining PR: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc


def main() -> None:
    """CLI entrypoint for gh-pr-examine command."""
    app()


__all__ = [
    "app",
    "discover_current_pr",
    "examine",
    "examine_pr",
    "main",
]
