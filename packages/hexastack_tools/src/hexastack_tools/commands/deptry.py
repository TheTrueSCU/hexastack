"""Deptry workspace dependency runner for Hexastack subpackages."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.utils.workspace import get_package_directories, get_repo_root

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
        "DEP002,DEP003,DEP004",
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
    table.add_column("Package", style="bold")
    table.add_column("Status", width=12)
    table.add_column("Details")

    for pkg_dir in get_package_directories(repo_root):
        ok, err = run_deptry_on_package(pkg_dir)
        rel_pkg = pkg_dir.name
        if ok:
            table.add_row(rel_pkg, "[bold green]PASSED[/bold green]", "")
        else:
            failed = True
            table.add_row(rel_pkg, "[bold red]FAILED[/bold red]", err)

    console.print(table)
    if failed:
        console.print(
            Panel(
                "[bold red]❌ Deptry detected undeclared or missing dependencies.[/bold red]",
                border_style="red",
            )
        )
        return 1

    console.print(
        Panel(
            "[bold green]✨ All package dependencies explicitly declared in pyproject.toml.[/bold green]",
            border_style="green",
        )
    )
    return 0


__all__ = [
    "main",
    "run_deptry_on_package",
]
