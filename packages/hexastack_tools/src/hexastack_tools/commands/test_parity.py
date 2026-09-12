"""Test Parity and Directory Integrity Checker for Hexastack.

Notes/Architectural Intent:
    Serves as a driving adapter CLI wrapping test parity inspection utilities in utils.test_parity.
"""

from __future__ import annotations

import argparse

from hexastack_tools.adapters.presenters.governance import (
    create_governance_presenter,
)
from hexastack_tools.ports.governance import GovernancePresenterPort
from hexastack_tools.utils.test_parity import (
    check_src_to_test_symmetry,
    check_test_directories_inits,
)
from hexastack_tools.utils.workspace import get_repo_root


def main(
    presenter: GovernancePresenterPort | None = None,
) -> int:
    """CLI entrypoint for check-test-parity.

    Args:
        presenter: Optional GovernancePresenterPort instance.

    Returns:
        0 if parity clean, 1 if violations found.
    """
    parser = argparse.ArgumentParser(
        prog="check-test-parity",
        description="Verify 1:1 symmetry between src modules and unit tests.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json", "markdown"],
        default="table",
        help="Output format (table, json, markdown). Default: table.",
    )
    args = parser.parse_args()

    root = get_repo_root()
    init_errors = check_test_directories_inits(root)
    symmetry_errors = check_src_to_test_symmetry(root)

    actual_presenter = presenter or create_governance_presenter(format_type=args.format)
    return actual_presenter.present_test_parity(init_errors, symmetry_errors)


__all__ = [
    "check_src_to_test_symmetry",
    "check_test_directories_inits",
    "main",
]
