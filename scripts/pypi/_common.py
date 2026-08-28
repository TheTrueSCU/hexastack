"""Shared utilities for PyPI monorepo build and release scripts.

Notes/Architectural Intent:
    Provides automated discovery of workspace packages under `packages/`,
    version validation, and PyPI JSON API querying without subprocess shelling.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from scripts._common import get_package_directories, get_repo_root

__all__ = [
    "PackageMetadata",
    "check_pypi_version_exists",
    "get_workspace_packages_metadata",
]


@dataclass(frozen=True)
class PackageMetadata:
    """Metadata for a discovered monorepo subpackage."""

    name: str
    version: str
    dir_path: Path
    pyproject_path: Path


def get_workspace_packages_metadata() -> list[PackageMetadata]:
    """Discover all packages in the workspace and extract their name and version.

    Returns:
        Sorted list of PackageMetadata instances.
    """
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
        except (tomllib.TOMLDecodeError, OSError):
            continue

    return sorted(packages, key=lambda p: p.name)


def check_pypi_version_exists(package_name: str, version: str) -> bool:
    """Check if a specific package version is already published on PyPI.

    Args:
        package_name: PyPI project name.
        version: Semantic version string.

    Returns:
        True if the release already exists on PyPI, False otherwise.
    """
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return False
            if resp.status_code == 200:
                data: dict[str, Any] = resp.json()
                releases = data.get("releases", {})
                return version in releases
    except (httpx.HTTPError, OSError):
        return False
    return False
