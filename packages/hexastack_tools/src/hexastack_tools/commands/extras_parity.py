"""Optional Extras Parity and Umbrella Forwarding Validator for Hexastack."""

from __future__ import annotations

import argparse

from hexastack_tools.adapters.presenters.dependency import create_dependency_presenter
from hexastack_tools.domain.dependencies import (
    AuditExtrasParityCommand,
    ExtraParityViolation,
    ExtrasAuditResult,
)
from hexastack_tools.infra.bootstrap import create_governance_bus
from hexastack_tools.utils.extras_parity import (
    audit_extras_parity,
    generate_extras_mermaid_diagram,
)
from hexastack_tools.utils.workspace import get_repo_root

__all__ = [
    "audit_extras_parity",
    "ExtraParityViolation",
    "generate_extras_mermaid_diagram",
    "main",
]


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for extras parity validator and diagram generator.

    Args:
        argv: Optional command-line arguments list.

    Returns:
        Exit code (0 for success, 1 for failures).
    """
    parser = argparse.ArgumentParser(
        description="Audit optional extras parity across workspace subpackages and umbrella package."
    )
    parser.add_argument(
        "--diagram",
        action="store_true",
        help="Generate and print Mermaid dependency diagram of package extras.",
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

    cmd = AuditExtrasParityCommand(
        repo_root=repo_root,
        generate_diagram=args.diagram,
    )
    result = bus.dispatch(cmd)

    if isinstance(result, str):
        return presenter.present_extras_parity(
            ExtrasAuditResult(violations=(), total_packages_checked=0),
            diagram=result,
        )
    return presenter.present_extras_parity(result)
