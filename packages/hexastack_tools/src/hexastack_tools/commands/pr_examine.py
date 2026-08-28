"""Unified Single-Step PR Examination CLI Command."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time

from rich.console import Console

from hexastack_tools.adapters.github import GitHubHttpAdapter
from hexastack_tools.adapters.presenters import (
    render_pr_summary_json,
    render_pr_summary_rich,
)

console = Console()


def discover_current_pr(client: GitHubHttpAdapter) -> int | None:
    """Discover open PR number for current local branch."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            return None
        current_branch = res.stdout.strip()
        if not current_branch or current_branch == "main":
            return None

        # Fetch open PRs matching branch
        resp = client._client.get(
            f"/repos/{client.owner}/{client.repo}/pulls",
            params={"head": f"{client.owner}:{current_branch}", "state": "open"},
        )
        if resp.status_code == 200:
            prs = resp.json()
            if prs:
                return int(prs[0]["number"])
    except Exception:
        return None
    return None


def examine_pr(
    pr_number: int | None = None,
    show_details: bool = False,
    output_format: str = "rich",
    watch: bool = False,
    watch_interval: int = 15,
) -> int:
    """Execute single-step PR inspection pipeline."""
    with GitHubHttpAdapter() as client:
        target_pr = pr_number or discover_current_pr(client)
        if not target_pr:
            console.print(
                "[bold yellow]No PR number provided and could not determine active PR for current branch.[/bold yellow]\n"
                "Usage: [bold cyan]gh-pr-examine <PR_NUMBER>[/bold cyan]"
            )
            return 1

        while True:
            summary = client.get_pr_summary(target_pr)

            if output_format == "json":
                print(render_pr_summary_json(summary))
            else:
                render_pr_summary_rich(summary, show_details=show_details)

            if not watch:
                break

            # If all checks are completed and PR is clean, finish watch loop
            in_progress = any(
                c.status.lower() in ("in_progress", "queued", "pending")
                for c in summary.check_runs
            )
            if not in_progress:
                console.print(
                    "\n[bold green]🏁 All check runs have finished execution![/bold green]"
                )
                break

            console.print(
                f"\n[dim]Watching PR #{target_pr}... (refreshing in {watch_interval}s)[/dim]"
            )
            time.sleep(watch_interval)

        return 0 if summary.is_clean else 1


def main() -> int:
    """CLI entrypoint for gh-pr-examine."""
    parser = argparse.ArgumentParser(
        description="Single-step comprehensive Pull Request inspector aggregating metadata, CI checks, security alerts, and review thread resolution."
    )
    parser.add_argument(
        "pr",
        nargs="?",
        type=int,
        default=None,
        help="Pull Request number (e.g. 41). Auto-detects current branch PR if omitted.",
    )
    parser.add_argument(
        "--details",
        "-d",
        action="store_true",
        default=False,
        help="Print detailed contextual panels for unresolved review conversations and findings.",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["rich", "json"],
        default="rich",
        help="Output presenter format ('rich', 'json').",
    )
    parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        default=False,
        help="Watch PR checks until all workflows finish execution.",
    )
    args = parser.parse_args()

    try:
        return examine_pr(
            pr_number=args.pr,
            show_details=args.details,
            output_format=args.format,
            watch=args.watch,
        )
    except Exception as exc:
        console.print(f"[bold red]Error examining PR:[/bold red] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
