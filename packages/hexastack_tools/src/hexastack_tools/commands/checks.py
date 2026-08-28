"""GitHub PR check auditor command powered by Typer and Presenters."""

from __future__ import annotations

from typing import Annotated

import typer

from hexastack_tools.adapters.github import GitHubHttpAdapter
from hexastack_tools.adapters.presenters.checks import present_checks
from hexastack_tools.domain.github import OutputFormat

app = typer.Typer(
    help="Inspect GitHub CI and status checks.",
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def checks(
    ref_or_pr: Annotated[
        str,
        typer.Argument(
            help="Pull request number or commit ref/branch name.",
        ),
    ],
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format: rich (interactive tables), json (structured), plain (TSV).",
        ),
    ] = OutputFormat.RICH,
) -> None:
    """Inspect CI status checks for a given PR number or Git ref."""
    try:
        with GitHubHttpAdapter() as client:
            if ref_or_pr.isdigit():
                summary = client.get_pr_summary(int(ref_or_pr))
                check_runs = list(summary.check_runs)
            else:
                check_runs = client.get_check_runs(ref_or_pr)

        present_checks(check_runs, ref_or_pr, output_format=output_format)
        has_failure = any(c.conclusion.lower() == "failure" for c in check_runs)
        if has_failure:
            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as exc:
        typer.secho(
            f"Error querying GitHub checks: {exc}", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1) from exc


def main() -> None:
    """CLI entrypoint for gh-checks."""
    app()


__all__ = ["app", "checks", "main"]
