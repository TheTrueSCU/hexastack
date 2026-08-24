"""Formatter to automatically alphabetize and deduplicate __all__ statements.

Notes/Architectural Intent:
    Normalizes `__all__` statements across specified or discovered modules.
    Supports package, path, and all options via shared HexastackScriptArgumentParser.
"""

import ast
from pathlib import Path

from scripts._common import (
    HexastackScriptArgumentParser,
    resolve_target_python_files,
)


def format_all_in_file(py_file: Path) -> bool:
    """Alphabetize and deduplicate __all__ in a python source file."""
    content = py_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(content, filename=str(py_file))
    except Exception:
        return False

    all_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    ]

    if not all_nodes:
        return False

    modified = False
    new_content = content

    for node in all_nodes:
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            continue

        symbols: list[str] = []
        for elt in node.value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                symbols.append(elt.value)

        # Deduplicate and sort alphabetically case-insensitively
        deduped = sorted(set(symbols), key=str.casefold)
        if deduped == symbols and len(deduped) == len(symbols):
            continue

        # Format clean replacement block
        formatted_list = "[\n" + "".join(f'    "{sym}",\n' for sym in deduped) + "]"

        # Replace the __all__ definition in source
        node_src = ast.get_source_segment(content, node)
        if node_src:
            new_node_src = f"__all__ = {formatted_list}"
            new_content = new_content.replace(node_src, new_node_src, 1)
            modified = True

    if modified:
        py_file.write_text(new_content, encoding="utf-8")
        return True
    return False


def main() -> None:
    """Format __all__ declarations in target Python files."""
    parser = HexastackScriptArgumentParser(
        description="Format, alphabetize, and deduplicate __all__ statements."
    )
    args = parser.parse_args()

    py_files = resolve_target_python_files(args)
    formatted_count = 0
    for py_file in py_files:
        if format_all_in_file(py_file):
            formatted_count += 1
    print(f"Formatted __all__ statements in {formatted_count} files.")


if __name__ == "__main__":
    main()
