"""PyPI Monorepo Distribution Builder, Checker, and Publisher."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import httpx
from rich.console import Console
from rich.table import Table

from hexastack_tools.utils.workspace import get_package_directories, get_repo_root

console = Console()


@dataclass(frozen=True)
class PackageMetadata:
    """Metadata for a discovered monorepo subpackage."""

    name: str
    version: str
    dir_path: Path
    pyproject_path: Path


def get_workspace_packages_metadata() -> list[PackageMetadata]:
    """Discover all packages in the workspace and extract their name and version."""
    repo_root = get_repo_root()
    pkg_dirs = get_package_directories(repo_root)
    packages: list[PackageMetadata] = []

    for pkg_dir in pkg_dirs:
        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.is_file():
            continue

        try:
            content = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = content.get("project", {})
            name = project.get("name")
            version = project.get("version")
            if name and version:
                packages.append(
                    PackageMetadata(
                        name=name,
                        version=version,
                        dir_path=pkg_dir,
                        pyproject_path=pyproject,
                    )
                )
        except Exception:
            continue

    return sorted(packages, key=lambda p: p.name)


def check_pypi_version_exists(package_name: str, version: str) -> bool:
    """Check if a specific package version is already released on PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return False
            if resp.status_code == 200:
                data = resp.json()
                releases = data.get("releases", {})
                return version in releases
    except Exception:
        return False
    return False


def build_all_packages(out_dir: Path | None = None) -> int:
    """Build distribution artifacts for all workspace packages."""
    repo_root = get_repo_root()
    target_dist = out_dir or (repo_root / "dist")
    target_dist.mkdir(parents=True, exist_ok=True)

    packages = get_workspace_packages_metadata()
    if not packages:
        return 1

    table = Table(
        title=f"[bold cyan]PyPI Monorepo Distribution Builder -> {target_dist}[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package Name", style="bold")
    table.add_column("Version", width=12)
    table.add_column("Status", width=16)

    failures: list[str] = []
    for pkg in packages:
        cmd = ["uv", "build", "--package", pkg.name, "--out-dir", str(target_dist)]
        res = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
        if res.returncode == 0:
            table.add_row(pkg.name, pkg.version, "[bold green]✓ Built[/bold green]")
        else:
            failures.append(pkg.name)
            table.add_row(pkg.name, pkg.version, "[bold red]✗ Failed[/bold red]")

    console.print(table)
    return 1 if failures else 0


def build_main() -> None:
    """CLI entrypoint for pypi-build."""
    sys.exit(build_all_packages())


def check_main() -> None:
    """CLI entrypoint for pypi-check."""
    parser = argparse.ArgumentParser(
        description="Verify package release version availability against PyPI index."
    )
    parser.parse_args()

    packages = get_workspace_packages_metadata()
    table = Table(
        title="[bold cyan]PyPI Release Version Availability Checker[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package Name", style="bold")
    table.add_column("Local Version", width=14)
    table.add_column("PyPI Status", width=20)

    for pkg in packages:
        exists = check_pypi_version_exists(pkg.name, pkg.version)
        status_styled = (
            "[yellow]Already Released[/yellow]"
            if exists
            else "[bold green]Available for Release[/bold green]"
        )
        table.add_row(pkg.name, pkg.version, status_styled)

    console.print(table)


def publish_main() -> None:
    """CLI entrypoint for pypi-publish."""
    parser = argparse.ArgumentParser(
        description="Build distribution packages and prepare for PyPI release publishing."
    )
    parser.parse_args()

    console.print("[bold cyan]Executing PyPI publishing pipeline...[/bold cyan]")
    build_all_packages()


__all__ = [
    "build_all_packages",
    "build_main",
    "check_main",
    "check_pypi_version_exists",
    "get_workspace_packages_metadata",
    "PackageMetadata",
    "publish_main",
]
