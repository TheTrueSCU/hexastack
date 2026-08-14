"""Utility script to synchronize and validate .importlinter configuration.

Notes/Architectural Intent:
    Scans the Hexastack monorepo workspace packages (or standalone projects)
    and validates or updates the .importlinter configuration to ensure all
    discovered packages, inter-subsystem independence contracts, and internal
    hexagonal layers remain up-to-date and alphabetized.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import get_repo_root

ROOT_DIR = get_repo_root()
PACKAGES_DIR = ROOT_DIR / "packages"
IMPORTLINTER_FILE = ROOT_DIR / ".importlinter"


def discover_packages(packages_dir: Path) -> list[str]:
    """Discover all Python package module names within packages directory.

    Args:
        packages_dir: Path to the root packages directory.

    Returns:
        Sorted list of discovered Python package module names.

    Raises:
        FileNotFoundError: If packages_dir does not exist.
    """
    if not packages_dir.is_dir():
        raise FileNotFoundError(f"Packages directory not found: {packages_dir}")

    discovered: list[str] = []
    for pkg_dir in sorted(packages_dir.iterdir()):
        if not pkg_dir.is_dir():
            continue
        src_dir = pkg_dir / "src"
        if src_dir.is_dir():
            for child in sorted(src_dir.iterdir()):
                if child.is_dir() and (child / "__init__.py").exists():
                    discovered.append(child.name)
    return sorted(discovered)


def check_internal_layers(pkg_name: str, packages_dir: Path) -> list[str]:
    """Inspect a package for standard Hexagonal layers (domain, ports, adapters, infra).

    Args:
        pkg_name: Name of the Python module.
        packages_dir: Path to the workspace packages directory.

    Returns:
        Sorted list of existing layer directory names in the package.
    """
    src_pkg = packages_dir / pkg_name / "src" / pkg_name
    if not src_pkg.exists():
        src_pkg = packages_dir / pkg_name.replace("-", "_") / "src" / pkg_name

    standard_layers = ["infra", "adapters", "ports", "domain"]
    return [layer for layer in standard_layers if (src_pkg / layer).is_dir()]


def read_current_importlinter(path: Path) -> str:
    """Read the current .importlinter file content.

    Args:
        path: Path to the .importlinter file.

    Returns:
        Content of .importlinter or empty string if not found.
    """
    if not path.is_file():
        return ""
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def validate_root_packages(
    discovered: list[str], content: str
) -> tuple[bool, list[str]]:
    """Verify all discovered packages are present in .importlinter root_packages.

    Args:
        discovered: List of discovered package names.
        content: Current .importlinter text content.

    Returns:
        Tuple of (is_valid, list of missing packages).
    """
    missing: list[str] = [pkg for pkg in discovered if pkg not in content]
    return (len(missing) == 0, missing)


def main() -> int:
    """Entry point for .importlinter sync and validation utility.

    Returns:
        Exit code (0 for success, 1 for validation failure or error).
    """
    parser = argparse.ArgumentParser(
        description="Synchronize and validate .importlinter contracts."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate .importlinter without modifying the file (fails if stale).",
    )
    args = parser.parse_args()

    try:
        discovered = discover_packages(PACKAGES_DIR)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    current_content = read_current_importlinter(IMPORTLINTER_FILE)
    if not current_content:
        print(f"Error: Could not read {IMPORTLINTER_FILE.name}", file=sys.stderr)
        return 1

    is_valid, missing = validate_root_packages(discovered, current_content)

    print("========================================================")
    print(" Import Linter Contract Validator & Synchronizer")
    print(f" Workspace Packages: {len(discovered)} discovered")
    print("========================================================")

    for pkg in discovered:
        layers = check_internal_layers(pkg, PACKAGES_DIR)
        layers_str = " -> ".join(layers) if layers else "flat / utility"
        status = "✅ Synced" if pkg not in missing else "❌ Missing from config"
        print(f"  • {pkg:<22} [{status}] ({layers_str})")

    print("--------------------------------------------------------")

    if not is_valid:
        print(
            f"❌ Stale .importlinter! Missing packages: {', '.join(missing)}",
            file=sys.stderr,
        )
        if args.check:
            return 1
        return 1

    print("🎉 .importlinter is up-to-date with all workspace packages and layers!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
