"""Script to alphabetize functions and methods across packages or targeted directories.

Notes/Architectural Intent:
    Serves as the batch runner wrapper around rope's AST sorting capabilities.
    Processes full packages or subtrees while preserving module headers, class
    docstrings, dunders, and main guards. Uses shared HexastackScriptArgumentParser.
"""

from __future__ import annotations

from scripts._common import (
    HexastackScriptArgumentParser,
    get_repo_root,
    resolve_target_python_files,
)
from scripts.rope.run import sort_python_file

ROOT_DIR = get_repo_root()


def main() -> None:
    """CLI entrypoint for batch alphabetization."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    parser = HexastackScriptArgumentParser(
        description="Alphabetize functions and class methods across packages deterministically."
    )
    args = parser.parse_args()

    py_files = resolve_target_python_files(args)
    if not py_files:
        console.print(
            Panel.fit(
                "[dim]No Python files found matching the criteria.[/dim]",
                border_style="dim",
            )
        )
        return

    # Process all collected files
    modified_count = 0
    for file_path in py_files:
        if sort_python_file(file_path):
            modified_count += 1
            console.print(
                f"  [cyan]Alphabetized:[/cyan] {file_path.relative_to(ROOT_DIR)}"
            )

    console.print()
    console.print(
        Panel.fit(
            f"[bold green]✨ Alphabetization complete: Processed {len(py_files)} file(s), {modified_count} modified.[/bold green]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
