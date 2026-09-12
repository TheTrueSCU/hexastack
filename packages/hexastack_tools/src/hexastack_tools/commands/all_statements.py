"""API Surface and __all__ integrity checker and formatter CLI for Hexastack codebase.

Notes/Architectural Intent:
    Serves as a driving adapter CLI wrapping pure AST utilities from utils.all_statements.
"""

from __future__ import annotations

import sys

from hexastack_tools.adapters.presenters.governance import (
    create_governance_presenter,
)
from hexastack_tools.ports.governance import GovernancePresenterPort
from hexastack_tools.utils.all_statements import (
    check_file_all,
    fix_file_all,
)
from hexastack_tools.utils.workspace import (
    HexastackScriptArgumentParser,
    resolve_target_python_files,
)


def main_check(
    presenter: GovernancePresenterPort | None = None,
) -> int:
    """Validate ``__all__`` declarations across targeted files.

    Args:
        presenter: Optional GovernancePresenterPort instance.

    Returns:
        0 if valid, 1 if violations found.
    """
    parser = HexastackScriptArgumentParser(
        description="Verify __all__ is deduplicated and sorted."
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json", "markdown"],
        default="table",
        help="Output format (table, json, markdown). Default: table.",
    )
    args = parser.parse_args()

    py_files = resolve_target_python_files(args)
    all_errors: list[str] = []

    for f in py_files:
        all_errors.extend(check_file_all(f))

    actual_presenter = presenter or create_governance_presenter(format_type=args.format)
    return actual_presenter.present_all_statements(all_errors)


def main_fix(
    presenter: GovernancePresenterPort | None = None,
) -> None:
    """Format ``__all__`` declarations in target Python files.

    Args:
        presenter: Optional GovernancePresenterPort instance.
    """
    parser = HexastackScriptArgumentParser(
        description="Format, alphabetize, and deduplicate __all__ statements."
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json", "markdown"],
        default="table",
        help="Output format (table, json, markdown). Default: table.",
    )
    args = parser.parse_args()

    py_files = resolve_target_python_files(args)
    formatted_count = sum(fix_file_all(f) for f in py_files)
    actual_presenter = presenter or create_governance_presenter(format_type=args.format)
    actual_presenter.present_all_statements([], modified_count=formatted_count)


def check_main() -> None:
    """CLI entrypoint for check-all-statements."""
    sys.exit(main_check())


def fix_main() -> None:
    """CLI entrypoint for fix-all-statements."""
    main_fix()


__all__ = [
    "check_file_all",
    "check_main",
    "fix_file_all",
    "fix_main",
    "main_check",
    "main_fix",
]
