"""API Surface & __all__ integrity checker and formatter for Hexastack codebase."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from hexastack_tools.utils.workspace import (
    HexastackScriptArgumentParser,
    resolve_target_python_files,
)


def _find_all_nodes(tree: ast.Module) -> list[ast.Assign]:
    """Return top-level ``__all__`` assignment nodes from a parsed module."""
    return [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    ]


def _extract_symbols(node: ast.Assign) -> list[str]:
    """Extract string literal elements from an ``__all__`` assignment node."""
    if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
        return [
            elt.value
            for elt in node.value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        ]
    return []


def check_file_all(py_file: Path) -> list[str]:
    """Inspect a single Python file for ``__all__`` integrity violations."""
    try:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
    except Exception:
        return []

    errors: list[str] = []
    for node in _find_all_nodes(tree):
        symbols = _extract_symbols(node)
        seen = set()
        duplicates = [s for s in symbols if s in seen or seen.add(s)]
        if duplicates:
            errors.append(
                f"{py_file}: Duplicate symbol(s) in __all__: {sorted(set(duplicates))}"
            )

        if isinstance(node.value, (ast.List, ast.Tuple)):
            sorted_symbols = sorted(symbols, key=str.casefold)
            if symbols != sorted_symbols:
                errors.append(
                    f"{py_file}: __all__ is not sorted alphabetically. Expected order: {sorted_symbols}"
                )

    return errors


def fix_file_all(py_file: Path) -> bool:
    """Format and alphabetize ``__all__`` declarations in a Python file."""
    try:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
    except Exception:
        return False

    modified = False
    new_content = content

    for node in _find_all_nodes(tree):
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            continue

        symbols = _extract_symbols(node)
        deduped = sorted(set(symbols), key=str.casefold)
        if deduped == symbols and len(deduped) == len(symbols):
            continue

        formatted_list = "[\n" + "".join(f'    "{sym}",\n' for sym in deduped) + "]"
        node_src = ast.get_source_segment(content, node)
        if node_src:
            new_content = new_content.replace(
                node_src, f"__all__ = {formatted_list}", 1
            )
            modified = True

    if modified:
        py_file.write_text(new_content, encoding="utf-8")
    return modified


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
