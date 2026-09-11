"""Deptry workspace dependency runner for Hexastack subpackages."""

from __future__ import annotations

import argparse
from pathlib import Path

from hexastack_tools.adapters.presenters.dependency import create_dependency_presenter
from hexastack_tools.adapters.runners.dependency_runner import (
    SubprocessDependencyAuditorAdapter,
)
from hexastack_tools.domain.dependencies import RunDeptryAuditCommand
from hexastack_tools.infra.bootstrap import create_governance_bus
from hexastack_tools.utils.workspace import (
    ensure_tool_installed,
    get_repo_root,
)

__all__ = [
    "main",
    "run_deptry_on_package",
]


def run_deptry_on_package(pkg_dir: Path) -> tuple[bool, str]:
    """Execute deptry check for a single package.

    Args:
        pkg_dir: Directory path of the target package.

    Returns:
        Tuple of (passed: bool, error_output: str).
    """
    res = SubprocessDependencyAuditorAdapter().run_deptry(pkg_dir)
    return res.passed, res.error_output


def main(argv: list[str] | None = None) -> int:
    """Run deptry across all workspace packages.

    Args:
        argv: Optional command-line arguments list.

    Returns:
        Exit code (0 for success, non-zero for failures).
    """
    ensure_tool_installed("deptry", cli_command="deptry", extra_name="governance")

    parser = argparse.ArgumentParser(description="Run deptry per package.")
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json", "markdown"],
        default="table",
        help="Output presentation format (default: table).",
    )
    args = parser.parse_args(argv)

    repo_root = get_repo_root()
    bus = create_governance_bus()
    presenter = create_dependency_presenter(args.format)

    cmd = RunDeptryAuditCommand(repo_root=repo_root)
    report = bus.dispatch(cmd)
    return presenter.present_deptry_audit(report)
