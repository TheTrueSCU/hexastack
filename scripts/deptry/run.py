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

from scripts._common import get_package_directories, get_repo_root


def run_deptry_on_package(pkg_dir: Path) -> bool:
    """Execute deptry check for a single package."""
    pyproject = pkg_dir / "pyproject.toml"
    if not pyproject.is_file():
        return True

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
        print(f"\n❌ [deptry] Undeclared dependencies in {pkg_dir.name}:")
        if res.stdout.strip():
            print(res.stdout)
        if res.stderr.strip():
            print(res.stderr)
        return False
    return True


def main() -> int:
    """Run deptry across all workspace packages."""
    parser = argparse.ArgumentParser(description="Run deptry per package.")
    parser.parse_args()

    repo_root = get_repo_root()
    failed = False

    for pkg_dir in get_package_directories(repo_root):
        if not run_deptry_on_package(pkg_dir):
            failed = True

    if not failed:
        print("✅ [deptry] All package dependency declarations are clean!")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
