#!/usr/bin/env python3
"""Programmatically generate architecture diagrams using pydeps."""

from pathlib import Path

from _common import get_package_directories, get_packages_directory, get_repo_root
from pydeps.pydeps import pydeps


def generate_package_diagram(pkg_path: Path) -> None:
    pkg_name = pkg_path.name
    src_dir = pkg_path / "src" / pkg_name
    output_file = pkg_path / f"{pkg_name}-architecture.svg"

    if not src_dir.is_dir():
        print(f"Skipping {pkg_name}: '{src_dir}' not found.")
        return

    print(f"Generating diagram for {pkg_name} -> {output_file.name}...")

    pydeps(
        fname=str(src_dir),
        cluster=True,
        max_bacon=2,
        only=[pkg_name],
        rankdir="TB",
        noshow=True,
        output=str(output_file),
    )


def generate_monorepo_diagram() -> None:
    """Generate high-level cross-package overview from the umbrella package."""
    umbrella_src = get_packages_directory() / "hexastack" / "src" / "hexastack"
    output_file = get_repo_root() / "hexastack-packages.svg"

    if not umbrella_src.is_dir():
        return

    print(f"Generating global monorepo diagram -> {output_file}...")
    pydeps(
        fname=str(umbrella_src),
        cluster=True,
        max_bacon=2,
        only=["hexastack"],
        max_module_depth=2,
        noshow=True,
        output=str(output_file),
    )


def main() -> None:
    # 1. Global package-level diagram
    generate_monorepo_diagram()

    # 2. Per-package internal hexagonal diagrams
    for pkg in get_package_directories():
        if pkg.is_dir() and (pkg / "pyproject.toml").is_file():
            generate_package_diagram(pkg)


if __name__ == "__main__":
    main()
