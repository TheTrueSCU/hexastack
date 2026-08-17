#!/usr/bin/env python3
"""Runner script for import-linter across packages in the monorepo."""

import argparse
import subprocess
import sys
from pathlib import Path

from _common import get_package_directories

PACKAGES_DIR = Path("packages")


def find_packages_to_lint(changed_files: list[str]) -> list[Path]:
    """Identify which package directories need linting based on modified files."""
    all_packages = get_package_directories()

    if not changed_files:
        # If no filenames passed (e.g. manual run or pass_filenames: false), check all
        return [p for p in all_packages if (p / "pyproject.toml").is_file()]

    affected_packages = set()
    for file_path_str in changed_files:
        path = Path(file_path_str)
        try:
            # Check if file resides under packages/<package_name>/
            rel = path.relative_to(PACKAGES_DIR)
            pkg_name = rel.parts[0]
            pkg_dir = PACKAGES_DIR / pkg_name
            if (pkg_dir / "pyproject.toml").is_file():
                affected_packages.add(pkg_dir)
        except ValueError:
            # File outside packages/ directory
            continue

    return sorted(affected_packages)


def run_linter_for_package(pkg_path: Path) -> bool:
    """Execute lint-imports using the package's pyproject.toml configuration."""
    config_file = pkg_path / "pyproject.toml"
    print(f"\n[import-linter] Checking {pkg_path.name}...")

    result = subprocess.run(
        ["lint-imports", "--config", str(config_file)],
        capture_output=False,
    )
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run import-linter per package.")
    parser.add_argument("files", nargs="*", help="Changed files passed by pre-commit")
    parser.add_argument(
        "--all", action="store_true", help="Run across all packages unconditionally"
    )
    args = parser.parse_args()

    if args.all:
        packages = [
            p for p in get_package_directories() if (p / "pyproject.toml").is_file()
        ]
    else:
        packages = find_packages_to_lint(args.files)

    if not packages:
        print("[import-linter] No package changes detected.")
        return 0

    failed = False
    for pkg in packages:
        success = run_linter_for_package(pkg)
        if not success:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
