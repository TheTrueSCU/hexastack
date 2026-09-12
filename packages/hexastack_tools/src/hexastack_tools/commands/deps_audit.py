"""Unified Workspace Dependency, Packaging Extras, and Architecture Auditor."""

from __future__ import annotations

import argparse
from pathlib import Path

from hexastack_tools.adapters.presenters.dependency import create_dependency_presenter
from hexastack_tools.domain.dependencies import RunUnifiedDepsAuditCommand
from hexastack_tools.infra.bootstrap import create_governance_bus
from hexastack_tools.utils.workspace import get_repo_root

__all__ = [
    "audit_workspace_dependencies",
    "main",
]


def audit_workspace_dependencies(
    repo_root: Path,
    *,
    check_deptry: bool = True,
    check_extras: bool = True,
    check_tools: bool = True,
    generate_diagrams: bool = False,
) -> tuple[bool, list[str]]:
    """Execute unified audit across packaging extras, source imports, tool binaries, and diagrams.

    Args:
        repo_root: Root directory of the repository workspace.
        check_deptry: Whether to run deptry import audits on each package.
        check_extras: Whether to run optional extras parity auditing.
        check_tools: Whether to verify tool dependency availability in current environment.
        generate_diagrams: Whether to regenerate Pydeps SVGs and Mermaid diagrams.

    Returns:
        Tuple of (is_healthy: bool, list_of_error_messages: list[str]).

    Notes/Architectural Intent:
        Unifies code-level import verification (deptry), tool dependency readiness,
        and pyproject.toml packaging forwarding contracts into a single high-performance pipeline.
    """
    bus = create_governance_bus()
    cmd = RunUnifiedDepsAuditCommand(
        repo_root=repo_root,
        check_deptry=check_deptry,
        check_extras=check_extras,
        check_tools=check_tools,
        generate_diagrams=generate_diagrams,
    )
    report = bus.dispatch(cmd)
    return report.is_healthy, list(report.errors)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for unified deps-audit command.

    Args:
        argv: Optional command-line arguments list.

    Returns:
        Exit code (0 for success, non-zero for failures).
    """
    parser = argparse.ArgumentParser(
        description="Unified dependency, optional extras, and architecture auditor for Hexastack."
    )
    parser.add_argument(
        "--diagrams",
        action="store_true",
        help="Regenerate all Pydeps SVG import graphs and Mermaid extras diagrams.",
    )
    parser.add_argument(
        "--deptry-only",
        action="store_true",
        help="Only run deptry source import audits.",
    )
    parser.add_argument(
        "--extras-only",
        action="store_true",
        help="Only run optional extras parity checks.",
    )
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

    check_deptry = not args.extras_only
    check_extras = not args.deptry_only

    cmd = RunUnifiedDepsAuditCommand(
        repo_root=repo_root,
        check_deptry=check_deptry,
        check_extras=check_extras,
        check_tools=True,
        generate_diagrams=args.diagrams,
    )
    report = bus.dispatch(cmd)
    return presenter.present_unified_deps_audit(report)
