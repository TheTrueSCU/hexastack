"""API Surface & __all__ integrity checker and formatter command."""

from __future__ import annotations

import sys

from scripts.pre_commit.all_statements import (
    main_check,
    main_fix,
)


def check_main() -> None:
    """CLI entrypoint for check-all-statements."""
    sys.exit(main_check())


def fix_main() -> None:
    """CLI entrypoint for fix-all-statements."""
    main_fix()


__all__ = [
    "check_main",
    "fix_main",
]
