"""API Surface and __all__ integrity checker and formatter CLI for Hexastack codebase.

Notes/Architectural Intent:
    Serves as a driving adapter CLI wrapping pure AST utilities from utils.all_statements.
"""

from __future__ import annotations

import sys

from hexastack_tools.utils.all_statements import (
    check_file_all,
    fix_file_all,
)
from hexastack_tools.utils.workspace import (
    HexastackScriptArgumentParser,
    resolve_target_python_files,
)


def main_check() -> int:
    """Validate ``__all__`` declarations across targeted files."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    parser = HexastackScriptArgumentParser(
        description="Verify __all__ is deduplicated and sorted."
    )
    args = parser.parse_args()

    py_files = resolve_target_python_files(args)
    all_errors: list[str] = []

    for f in py_files:
        all_errors.extend(check_file_all(f))

    if all_errors:
        table = Table(
            title="[bold red]API Surface & __all__ Integrity Violations[/bold red]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Location & Violation")
        for err in all_errors:
            table.add_row(err)
        console.print(table)
        return 1

    return 0


def main_fix() -> None:
    """Format ``__all__`` declarations in target Python files."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    parser = HexastackScriptArgumentParser(
        description="Format, alphabetize, and deduplicate __all__ statements."
    )
    args = parser.parse_args()

    py_files = resolve_target_python_files(args)
    formatted_count = sum(fix_file_all(f) for f in py_files)
    console.print(
        Panel.fit(
            f"[bold green]✨ Formatted and alphabetized __all__ statements in {formatted_count} file(s).[/bold green]",
            border_style="green",
        )
    )


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
