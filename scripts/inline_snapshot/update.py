"""Snapshot creation and update utility for Hexastack test suites.

Notes/Architectural Intent:
    inline-snapshot requires a single-process (no xdist) run to write updated
    snapshots back into source files. This script provides a consistent,
    ergonomic interface for the three inline-snapshot modes:

    - create:  Record new snapshot() calls that have no existing value.
    - fix:     Update existing snapshots whose values have changed.
    - review:  Show a diff of all pending snapshot changes without applying them.

    Normal CI runs use xdist (parallel) and snapshots continue to pass read-only.
    Only use this script when you intentionally want to write or update snapshots.

Usage:
    # Fix stale snapshots in a package
    uv run python scripts/inline_snapshot/update.py -p core --mode fix

    # Create new snapshots in specific paths
    uv run python scripts/inline_snapshot/update.py --path packages/hexastack_cqrs --mode create

    # Run against all packages
    uv run python scripts/inline_snapshot/update.py -a --mode fix
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from scripts._common import (
    VALID_PACKAGES,
    HexastackScriptArgumentParser,
    get_package_directory,
    get_repo_root,
)

ROOT_DIR = get_repo_root()
VALID_MODES = ["create", "fix", "review"]


def run_snapshot_update_for_dir(target_dir: Path, mode: str) -> int:
    """Run pytest in single-process snapshot mode for the target directory.

    Args:
        target_dir: Path to directory containing tests to run.
        mode: inline-snapshot mode — one of 'create', 'fix', or 'review'.

    Returns:
        Exit code from the pytest subprocess (0 for success).
    """
    if not target_dir.is_dir():
        print(f"Error: Target directory not found: {target_dir}", file=sys.stderr)
        return 1

    cmd = [
        "uv",
        "run",
        "pytest",
        str(target_dir),
        "-v",
        "--no-cov",
        "-p",
        "no:xdist",  # Disable parallel execution — required for inline-snapshot writes
        "--override-ini=addopts=--import-mode=importlib",  # Strip -n auto from pyproject addopts
        f"--inline-snapshot={mode}",
    ]

    print(f"  → Running inline-snapshot [{mode}] for {target_dir.name}...")
    print(f"  → Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=ROOT_DIR)

    # inline-snapshot exits with code 1 on first `create` run due to expected
    # teardown warnings ("your snapshot is missing one value"). The snapshots
    # ARE written. A subsequent normal pytest run will pass cleanly.
    if mode == "create" and result.returncode == 1:
        print(
            "\n  ℹ️  Exit code 1 is expected on first 'create' run.\n"
            "     Snapshots have been written. Run normal pytest to verify.\n"
        )
        return 0

    return result.returncode


def _resolve_target_dirs(args: argparse.Namespace) -> list[Path]:
    """Resolve target package or test directories based on CLI options."""
    root = ROOT_DIR
    target_dirs: list[Path] = []

    # 1. Custom paths or positional files
    explicit = (getattr(args, "files", None) or []) + (
        getattr(args, "custom_paths", None) or []
    )
    if explicit:
        for p in explicit:
            path = Path(p) if Path(p).is_absolute() else (root / p)
            if path.exists():
                target_dirs.append(path)
        return sorted(target_dirs)

    # 2. Specific packages
    packages = getattr(args, "packages", None)
    if packages:
        for pkg_name in packages:
            pkg_dir = get_package_directory(pkg_name, root)
            if pkg_dir.is_dir():
                target_dirs.append(pkg_dir)
        return sorted(target_dirs)

    # 3. Default or --all: All packages
    for pkg_name in VALID_PACKAGES:
        pkg_dir = get_package_directory(pkg_name, root)
        if pkg_dir.is_dir():
            target_dirs.append(pkg_dir)
    return sorted(target_dirs)


def main() -> int:
    """Entry point for snapshot update utility."""
    parser = HexastackScriptArgumentParser(
        description="Create or fix inline-snapshots for Hexastack test suites."
    )
    parser.add_argument(
        "-m",
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

    targets = _resolve_target_dirs(args)
    if not targets:
        print("No target package directories found.", file=sys.stderr)
        return 1

    print("=" * 60)
    print(f"  Hexastack Snapshot Updater  [mode: {args.mode}]")
    print(f"  Targets: {', '.join(t.name for t in targets)}")
    print("=" * 60 + "\n")

    failed: list[str] = []
    for target in targets:
        code = run_snapshot_update_for_dir(target, args.mode)
        if code != 0:
            failed.append(target.name)

    print("\n" + "=" * 60)
    if failed:
        print(f"❌ Snapshot update failed for: {', '.join(failed)}")
        return 1

    print(
        f"✅ Snapshot [{args.mode}] complete for: {', '.join(t.name for t in targets)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
