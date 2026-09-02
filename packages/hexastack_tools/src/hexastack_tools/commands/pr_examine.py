"""Single-step PR Examination and Verification Tool powered by Typer and Presenters."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from typing import Annotated, Any

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


def _fetch_failed_ci_logs(
    client: GitHubHttpAdapter,
    check_runs: tuple[Any, ...],
) -> dict[str, str]:
    """Extract failed CI logs from check runs."""
    failed_logs: dict[str, str] = {}
    for c in check_runs:
        if getattr(c, "conclusion", "").lower() != "failure":
            continue
        url = getattr(c, "details_url", "")
        if "/actions/runs/" not in url:
            continue
        try:
            run_id = url.split("/actions/runs/")[1].split("/")[0]
            log_text = client.get_failed_run_logs(run_id)
            if log_text:
                failed_logs[getattr(c, "name", "job")] = log_text
        except Exception:
            pass
    return failed_logs


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

            failed_logs = _fetch_failed_ci_logs(client, summary.check_runs)
            present_pr_summary(
                summary,
                output_format=output_format,
                show_details=show_details,
                failed_logs=failed_logs if failed_logs else None,
            )

            if not watch:
                return 0 if summary.is_clean else 1

            time.sleep(poll_interval)


@app.callback(invoke_without_command=True)
def examine(
    ctx: typer.Context,
    pr_number: Annotated[
        str | None,
        typer.Argument(
            help="Pull request number (defaults to current branch PR).",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            "-f",
            help="Output format: auto (detects pipes), rich (interactive panels), json (structured), plain (TSV).",
        ),
    ] = OutputFormat.AUTO,
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
    if ctx.invoked_subcommand is not None:
        return

    # If pr_number is 'runs', dispatch to runs subcommand
    if pr_number == "runs":
        return

    target_pr: int | None = None
    if pr_number is not None:
        if pr_number.isdigit():
            target_pr = int(pr_number)
        else:
            typer.secho(
                f"Error: '{pr_number}' is not a valid PR number.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

    try:
        code = examine_pr(
            pr_number=target_pr,
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


@app.command()
def runs(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="Branch name to inspect workflow runs for (defaults to current branch).",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-n",
            help="Number of recent workflow runs to list.",
        ),
    ] = 5,
) -> None:
    """List recent GitHub Actions workflow runs for a branch."""
    target_branch = branch
    if not target_branch and shutil.which("git"):
        try:
            res = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False,
            )
            target_branch = res.stdout.strip() or None
        except Exception:
            pass

    with GitHubHttpAdapter() as client:
        runs_list = client.get_workflow_runs(branch=target_branch, limit=limit)

    if not runs_list:
        console.print(
            f"[yellow]No workflow runs found for branch '{target_branch}'.[/yellow]"
        )
        return

    from rich.table import Table

    table = Table(
        title=f"[bold cyan]Workflow Runs ({target_branch or 'all branches'})[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Run ID", style="dim", width=14)
    table.add_column("Workflow / Name", style="bold")
    table.add_column("Event", width=14)
    table.add_column("Status", width=12)
    table.add_column("Conclusion", width=16)
    table.add_column("Details URL", style="blue")

    for r in runs_list:
        conclusion = r.get("conclusion") or r.get("status") or "unknown"
        conc_styled = (
            "[bold green]✓ SUCCESS[/bold green]"
            if conclusion.lower() == "success"
            else "[bold red]✗ FAILURE[/bold red]"
            if conclusion.lower() == "failure"
            else f"[yellow]⏳ {conclusion.upper()}[/yellow]"
        )
        table.add_row(
            str(r.get("databaseId") or "-"),
            r.get("name") or r.get("displayTitle") or "-",
            r.get("event") or "-",
            r.get("status") or "-",
            conc_styled,
            r.get("url") or "-",
        )

    console.print(table)


def main() -> None:
    """CLI entrypoint for gh-pr-examine command."""
    app()


__all__ = [
    "app",
    "discover_current_pr",
    "examine",
    "examine_pr",
    "main",
    "runs",
]
