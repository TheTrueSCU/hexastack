"""AST parsing utilities for __all__ integrity checking and auto-sorting.

Notes/Architectural Intent:
    Pure AST traversal utility functions for inspecting and formatting __all__
    declarations without dependencies on framework layers.
"""

from __future__ import annotations

import ast
from pathlib import Path

__all__ = [
    "check_file_all",
    "fix_file_all",
]


def _find_all_nodes(tree: ast.Module) -> list[ast.Assign]:
    """Return top-level __all__ assignment nodes from a parsed module."""
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
    """Extract string literal elements from an __all__ assignment node."""
    if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
        return [
            elt.value
            for elt in node.value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        ]
    return []


def check_file_all(py_file: Path) -> list[str]:
    """Inspect a single Python file for __all__ integrity violations.

    Args:
        py_file: Path to Python source file.

    Returns:
        List of violation description strings.
    """
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
    """Format and alphabetize __all__ declarations in a Python file.

    Args:
        py_file: Path to Python source file.

    Returns:
        True if the file was modified, False otherwise.
    """
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
