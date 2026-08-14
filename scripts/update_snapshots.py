"""Snapshot creation and update utility for Hexastack test suites.

Notes/Architectural Intent:
    inline-snapshot requires a single-process (no xdist) run to write updated
    snapshots back into source files. This script provides a consistent,
    ergonomic interface for the two inline-snapshot modes:

    - create:  Record new snapshot() calls that have no existing value.
    - fix:     Update existing snapshots whose values have changed.
    - review:  Show a diff of all pending snapshot changes without applying them.

    Normal CI runs use xdist (parallel) and snapshots continue to pass read-only.
    Only use this script when you intentionally want to write or update snapshots.

Usage:
    # Create new snapshots in a package
    uv run python scripts/update_snapshots.py --package cqrs --mode create

    # Fix stale snapshots after a schema change
    uv run python scripts/update_snapshots.py --package events --mode fix

    # Review pending changes without writing them
    uv run python scripts/update_snapshots.py --package grpc --mode review

    # Run against all packages
    uv run python scripts/update_snapshots.py --all --mode fix
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from _common import VALID_PACKAGES, get_repo_root

ROOT_DIR = get_repo_root()

VALID_MODES = ["create", "fix", "review"]


def run_snapshot_update(package: str, mode: str) -> int:
    """Run pytest in single-process snapshot mode for the given package.

    Args:
        package: Short package name (e.g. 'cqrs', 'events', 'grpc').
        mode: inline-snapshot mode — one of 'create', 'fix', or 'review'.

    Returns:
        Exit code from the pytest subprocess (0 for success).

    Notes/Architectural Intent:
        Explicitly disables xdist via ``-p no:xdist`` so that inline-snapshot
        can write back to source files. Coverage is disabled (``--no-cov``) to
        keep output clean and avoid partial-coverage threshold failures when
        running a single package.
    """
    pkg_dir = ROOT_DIR / "packages" / f"hexastack_{package}"
    if not pkg_dir.is_dir():
        print(f"Error: Package directory not found: {pkg_dir}", file=sys.stderr)
        return 1

    cmd = [
        "uv",
        "run",
        "pytest",
        str(pkg_dir),
        "-v",
        "--no-cov",
        "-p",
        "no:xdist",  # Disable parallel execution — required for inline-snapshot writes
        f"--inline-snapshot={mode}",
    ]

    print(f"  → Running inline-snapshot [{mode}] for hexastack_{package}...")
    print(f"  → Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=ROOT_DIR)
    return result.returncode


def main() -> int:
    """Entry point for snapshot update utility.

    Returns:
        Exit code (0 for success, 1 for any failure).
    """
    parser = argparse.ArgumentParser(
        description="Create or fix inline-snapshots for Hexastack test suites.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--package",
        choices=VALID_PACKAGES,
        metavar="PACKAGE",
        help=f"Package to update snapshots for. One of: {', '.join(VALID_PACKAGES)}",
    )
    group.add_argument(
        "--all",
        action="store_true",
        dest="all_packages",
        help="Run snapshot update across all packages sequentially.",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default="fix",
        help=(
            "Snapshot mode: 'create' records new snapshots, "
            "'fix' updates stale ones, 'review' shows a diff without writing. "
            "Default: fix"
        ),
    )
    args = parser.parse_args()

    packages = VALID_PACKAGES if args.all_packages else [args.package]

    print("=" * 60)
    print(f"  Hexastack Snapshot Updater  [mode: {args.mode}]")
    print(f"  Packages: {', '.join(packages)}")
    print("=" * 60 + "\n")

    failed: list[str] = []
    for pkg in packages:
        code = run_snapshot_update(pkg, args.mode)
        if code != 0:
            failed.append(pkg)

    print("\n" + "=" * 60)
    if failed:
        print(f"❌ Snapshot update failed for: {', '.join(failed)}")
        return 1

    print(f"✅ Snapshot [{args.mode}] complete for: {', '.join(packages)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
