"""PyPI Dry-Run and Publication Helper.

Notes/Architectural Intent:
    Provides local dry-run validation and publishing helper with token discovery.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from scripts._common import get_repo_root
from scripts.pypi.build import build_all_packages

__all__ = [
    "main",
    "publish_packages",
]

console = Console()


def publish_packages(
    dist_dir: Path | None = None,
    dry_run: bool = True,
    token: str | None = None,
) -> int:
    """Publish distribution packages to PyPI with dry-run support.

    Args:
        dist_dir: Target directory containing built wheels/tarballs.
        dry_run: If True, execute dry-run check without uploading.
        token: Optional PyPI API token.

    Returns:
        0 on success, 1 on failure.
    """
    repo_root = get_repo_root()
    target_dist = dist_dir or (repo_root / "dist")

    if not target_dist.is_dir() or not list(target_dist.glob("*")):
        console.print(
            f"[cyan]No existing artifacts in '{target_dist}'. Building all packages first...[/cyan]"
        )
        build_rc = build_all_packages(out_dir=target_dist)
        if build_rc != 0:
            return build_rc

    files = list(target_dist.glob("*"))
    console.print(
        f"\n[bold cyan]Found {len(files)} distribution artifacts to publish from '{target_dist}':[/bold cyan]"
    )
    for f in sorted(files):
        console.print(f"  • {f.name} ({f.stat().st_size:,} bytes)")

    cmd = ["uv", "publish"]
    if dry_run:
        cmd.append("--dry-run")
        console.print(
            "\n[bold yellow]🔍 Running in DRY-RUN mode (no packages will be published to PyPI).[/bold yellow]\n"
        )

    pypi_token = token or os.getenv("PYPI_API_TOKEN") or os.getenv("UV_PUBLISH_TOKEN")
    env = os.environ.copy()
    if pypi_token:
        env["UV_PUBLISH_TOKEN"] = pypi_token

    cmd.extend([str(f) for f in target_dist.glob("*")])
    res = subprocess.run(cmd, cwd=str(repo_root), env=env, check=False)
    return res.returncode


def monitor_release_workflow() -> int:
    """Monitor recent GitHub Release & Publish workflow runs.

    Returns:
        0 if clean, 1 on failure.
    """
    from rich.table import Table

    from scripts.github._client import GitHubClient

    with GitHubClient() as client:
        runs = client.list_workflow_runs(workflow_name_or_file="release.yml", limit=5)

    if not runs:
        console.print(
            "[yellow]No recent runs found for 'release.yml' workflow.[/yellow]"
        )
        return 0

    table = Table(
        title="[bold cyan]GitHub Actions: Release & Publish Workflow Runs[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Run ID", style="dim", width=12)
    table.add_column("Event / Name", style="bold")
    table.add_column("Branch / Tag", width=16)
    table.add_column("Status", width=12)
    table.add_column("Conclusion", width=16)
    table.add_column("Run URL", style="blue")

    for r in runs:
        run_id = str(r.get("id", "-"))
        name = r.get("display_title") or r.get("name") or "release"
        branch = r.get("head_branch") or "-"
        status = r.get("status", "unknown")
        conc = r.get("conclusion") or "in_progress"
        url = r.get("html_url", "")

        if conc == "success":
            conc_styled = "[bold green]✓ success[/bold green]"
        elif conc == "failure":
            conc_styled = "[bold red]✗ failure[/bold red]"
        else:
            conc_styled = f"[cyan]{conc}[/cyan]"

        table.add_row(run_id, name, branch, status, conc_styled, url)

    console.print(table)
    return 0


def main() -> int:
    """CLI entrypoint for pypi-publish script."""
    parser = argparse.ArgumentParser(
        description="Publish monorepo distribution packages to PyPI or monitor release workflow."
    )
    parser.add_argument(
        "--dist-dir",
        "-d",
        type=Path,
        default=None,
        help="Directory containing built distribution archives.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Perform actual live publish to PyPI (defaults to dry-run).",
    )
    parser.add_argument(
        "--monitor",
        "-m",
        action="store_true",
        help="Query and display recent GitHub Actions release workflow runs.",
    )
    args = parser.parse_args()

    if args.monitor:
        return monitor_release_workflow()

    return publish_packages(dist_dir=args.dist_dir, dry_run=not args.live)


if __name__ == "__main__":
    sys.exit(main())
