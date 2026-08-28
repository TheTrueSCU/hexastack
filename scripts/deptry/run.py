"""Deptry workspace dependency runner for Hexastack subpackages.

Notes/Architectural Intent:
    Iterates over every package directory inside `packages/`, invoking `deptry`
    to ensure dependencies are explicitly declared per package, preventing
    undeclared leaks in a monorepo workspace.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts._common import get_package_directories, get_repo_root

console = Console()


def run_deptry_on_package(pkg_dir: Path) -> tuple[bool, str]:
    """Execute deptry check for a single package."""
    pyproject = pkg_dir / "pyproject.toml"
    if not pyproject.is_file():
        return True, ""

    cmd = [
        "deptry",
        str(pkg_dir),
        "--config",
        str(pyproject),
        "--known-first-party",
        pkg_dir.name,
        "--ignore",
        "DEP002,DEP003,DEP004",  # Ignore unused/transitive/dev across workspace optional extras
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        err_msg = (res.stdout.strip() + "\n" + res.stderr.strip()).strip()
        return False, err_msg
    return True, ""


def main() -> int:
    """Run deptry across all workspace packages."""
    parser = argparse.ArgumentParser(description="Run deptry per package.")
    parser.parse_args()

    repo_root = get_repo_root()
    failed = False

    table = Table(
        title="[bold cyan]Deptry Workspace Dependency Auditor[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package", style="bold white", width=25)
    table.add_column("Status", width=35)

    errors = []
    for pkg_dir in get_package_directories(repo_root):
        success, err = run_deptry_on_package(pkg_dir)
        if success:
            table.add_row(pkg_dir.name, "[bold green]CLEAN[/bold green]")
        else:
            table.add_row(pkg_dir.name, "[bold red]UNDECLARED DEPENDENCIES[/bold red]")
            errors.append((pkg_dir.name, err))
            failed = True

    console.print()
    console.print(table)
    console.print()

    if failed:
        for pkg_name, err in errors:
            console.print(f"[bold red]❌ Issues in {pkg_name}:[/bold red]\n{err}\n")
        return 1

    console.print(
        Panel.fit(
            "[bold green]✅ All package dependency declarations are explicitly declared and clean![/bold green]",
            border_style="green",
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
