"""Test Parity and Directory Integrity Checker for Hexastack.

Notes/Architectural Intent:
    Serves as a driving adapter CLI wrapping test parity inspection utilities in utils.test_parity.
"""

from __future__ import annotations

from hexastack_tools.utils.test_parity import (
    check_src_to_test_symmetry,
    check_test_directories_inits,
)
from hexastack_tools.utils.workspace import get_repo_root


def main() -> int:
    """CLI entrypoint for check-test-parity."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    root = get_repo_root()

    init_errors = check_test_directories_inits(root)
    symmetry_errors = check_src_to_test_symmetry(root)
    all_errors = init_errors + symmetry_errors

    if all_errors:
        table = Table(
            title="[bold red]❌ Test Parity & Directory Integrity Violations[/bold red]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Violation Type", width=24, style="bold red")
        table.add_column("Details")

        for err in init_errors:
            table.add_row("Missing __init__.py", err)
        for err in symmetry_errors:
            table.add_row("Asymmetry / Missing Test", err)

        console.print(table)
        return 1

    console.print(
        Panel(
            "[bold green]✅ All source modules mirror unit tests 1:1 and all test directories contain __init__.py.[/bold green]",
            border_style="green",
        )
    )
    return 0


__all__ = [
    "check_src_to_test_symmetry",
    "check_test_directories_inits",
    "main",
]
