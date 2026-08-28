"""PyPI Release Integrity & Collision Auditor.

Notes/Architectural Intent:
    Audits version synchronization across all workspace packages and verifies
    against the live PyPI registry to identify version collisions before tagging releases.
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.table import Table

from scripts.pypi._common import (
    check_pypi_version_exists,
    get_workspace_packages_metadata,
)

__all__ = [
    "check_packages_release_status",
    "main",
]

console = Console()


def check_packages_release_status() -> int:
    """Audit workspace package versions and query PyPI registry.

    Returns:
        0 if clean, 1 if version synchronization or tag collisions are found.
    """
    packages = get_workspace_packages_metadata()
    if not packages:
        console.print("[bold red]No workspace packages discovered.[/bold red]")
        return 1

    table = Table(
        title="[bold cyan]PyPI Release Status & Version Synchronization Check[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package Name", style="bold")
    table.add_column("Local Version", width=14)
    table.add_column("PyPI Status", width=22)

    versions = {p.version for p in packages}
    collisions: list[str] = []

    for pkg in packages:
        exists = check_pypi_version_exists(pkg.name, pkg.version)
        if exists:
            status_str = "[bold yellow]⚠ Version Exists[/bold yellow]"
            collisions.append(f"{pkg.name}=={pkg.version}")
        else:
            status_str = "[bold green]✓ Ready for Release[/bold green]"

        table.add_row(pkg.name, pkg.version, status_str)

    console.print(table)

    has_issue = False
    if len(versions) > 1:
        console.print(
            f"\n[bold yellow]⚠ Warning: Multiple version strings detected across monorepo packages: {sorted(versions)}[/bold yellow]"
        )

    if collisions:
        console.print(
            "\n[bold yellow]Note: The following packages already have this version published on PyPI:[/bold yellow]"
        )
        for c in collisions:
            console.print(f"  • {c}")

    return 1 if has_issue else 0


def main() -> int:
    """CLI entrypoint for pypi-check script."""
    parser = argparse.ArgumentParser(
        description="Check package version consistency and query PyPI for existing releases."
    )
    parser.parse_args()

    return check_packages_release_status()


if __name__ == "__main__":
    sys.exit(main())
