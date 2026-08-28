"""Snapshot creation and update utility for Hexastack test suites."""

from __future__ import annotations

import subprocess
from pathlib import Path

from hexastack_tools.utils.workspace import (
    HexastackScriptArgumentParser,
    get_package_directories,
    get_package_directory,
    get_repo_root,
)

ROOT_DIR = get_repo_root()
VALID_MODES = ["create", "fix", "review"]


def run_snapshot_update_for_dir(target_dir: Path, mode: str) -> int:
    """Run pytest in single-process snapshot mode for the target directory."""
    if not target_dir.is_dir():
        return 1

    cmd = [
        "uv",
        "run",
        "pytest",
        str(target_dir),
        "-n",
        "0",
        f"--inline-snapshot={mode}",
        "--no-cov",
        "-o",
        "addopts=",
    ]
    res = subprocess.run(cmd, cwd=ROOT_DIR)
    return res.returncode


def main() -> int:
    """CLI entrypoint for inline-snapshot-update."""
    parser = HexastackScriptArgumentParser(
        description="Update or review inline-snapshots across Hexastack test suites."
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=VALID_MODES,
        default="fix",
        help="inline-snapshot mode: 'create' for new snapshots, 'fix' to update changed values, 'review' to diff (default: fix).",
    )
    args = parser.parse_args()

    targets: list[Path] = []
    if args.files:
        targets.extend(Path(f) for f in args.files)
    elif args.custom_paths:
        targets.extend(Path(p) for p in args.custom_paths)
    elif args.packages:
        targets.extend(get_package_directory(p, ROOT_DIR) for p in args.packages)
    elif args.all:
        targets.extend(get_package_directories(ROOT_DIR))
    else:
        targets.extend(get_package_directories(ROOT_DIR))

    exit_code = 0
    for target in targets:
        code = run_snapshot_update_for_dir(target, args.mode)
        if code != 0:
            exit_code = code

    return exit_code


__all__ = [
    "main",
    "run_snapshot_update_for_dir",
]
