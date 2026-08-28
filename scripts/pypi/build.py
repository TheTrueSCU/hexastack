"""PyPI Monorepo Distribution Builder.

Notes/Architectural Intent:
    Dynamically builds distribution wheels (.whl) and source archives (.tar.gz)
    for all discovered subpackages inside `packages/` into a unified `dist/` directory.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from scripts._common import get_repo_root
from scripts.pypi._common import get_workspace_packages_metadata

__all__ = [
    "build_all_packages",
    "main",
]

console = Console()


def build_all_packages(out_dir: Path | None = None) -> int:
    """Build distribution artifacts for all workspace packages.

    Args:
        out_dir: Target output directory (defaults to repo_root / 'dist').

    Returns:
        0 on success, 1 on any package build failure.
    """
    repo_root = get_repo_root()
    target_dist = out_dir or (repo_root / "dist")
    target_dist.mkdir(parents=True, exist_ok=True)

    packages = get_workspace_packages_metadata()
    if not packages:
        console.print(
            "[bold red]No workspace packages discovered for build.[/bold red]"
        )
        return 1

    table = Table(
        title=f"[bold cyan]PyPI Monorepo Distribution Builder -> {target_dist}[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package Name", style="bold")
    table.add_column("Version", width=12)
    table.add_column("Source Directory", style="dim")
    table.add_column("Status", width=16)

    failures: list[str] = []

    for pkg in packages:
        cmd = [
            "uv",
            "build",
            "--package",
            pkg.name,
            "--out-dir",
            str(target_dist),
        ]
        res = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            table.add_row(
                pkg.name,
                pkg.version,
                str(pkg.dir_path.relative_to(repo_root)),
                "[bold green]✓ Built[/bold green]",
            )
        else:
            table.add_row(
                pkg.name,
                pkg.version,
                str(pkg.dir_path.relative_to(repo_root)),
                "[bold red]✗ Failed[/bold red]",
            )
            failures.append(f"{pkg.name}: {res.stderr.strip() or res.stdout.strip()}")

    console.print(table)

    if failures:
        console.print("\n[bold red]Build Errors Encountered:[/bold red]")
        for fail in failures:
            console.print(f"  • {fail}")
        return 1

    built_artifacts = list(target_dist.glob("*"))
    console.print(
        f"\n[bold green]🎉 Successfully built {len(built_artifacts)} distribution artifacts in '{target_dist}'.[/bold green]"
    )
    return 0


def main() -> int:
    """CLI entrypoint for pypi-build script."""
    parser = argparse.ArgumentParser(
        description="Build distribution artifacts for all Hexastack monorepo packages."
    )
    parser.add_argument(
        "--out-dir",
        "-o",
        type=Path,
        default=None,
        help="Target distribution output directory (default: dist/).",
    )
    args = parser.parse_args()

    return build_all_packages(out_dir=args.out_dir)


if __name__ == "__main__":
    sys.exit(main())
