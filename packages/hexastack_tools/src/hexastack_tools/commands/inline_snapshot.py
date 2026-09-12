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


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for inline-snapshot-update.

    Args:
        argv: Optional command-line arguments list.

    Returns:
        Exit code (0 for success, non-zero for test failures).

    Notes/Architectural Intent:
        Dispatches UpdateInlineSnapshotsCommand across the governance bus and renders
        results via the configured AnalysisPresenterPort.
    """
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
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json", "markdown"],
        default="table",
        help="Output presentation format (default: table).",
    )
    args = parser.parse_args(argv)

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

    from hexastack_tools.adapters.presenters.analysis import (
        create_analysis_presenter,
    )
    from hexastack_tools.domain.analysis import UpdateInlineSnapshotsCommand
    from hexastack_tools.infra.bootstrap import create_governance_bus

    bus = create_governance_bus()
    presenter = create_analysis_presenter(args.format)

    cmd = UpdateInlineSnapshotsCommand(
        targets=tuple(targets),
        mode=args.mode,
    )
    report = bus.dispatch(cmd)
    return presenter.present_inline_snapshots(report)


__all__ = [
    "main",
    "run_snapshot_update_for_dir",
]
