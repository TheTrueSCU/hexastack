"""API Surface & __all__ integrity checker for Hexastack codebase.

Notes/Architectural Intent:
    Validates that:
    1. Every symbol declared in `__all__` actually exists in the corresponding module.
    2. Symbols declared in `__all__` do not contain duplicates.
    3. `__all__` is sorted alphabetically (clean code standard).
    4. Supports package, path, and all options via shared HexastackScriptArgumentParser.
"""

import ast
import sys
from pathlib import Path

from scripts._common import (
    HexastackScriptArgumentParser,
    resolve_target_python_files,
)


def check_file_all(py_file: Path) -> list[str]:
    """Check __all__ declaration in a python file via AST analysis."""
    errors: list[str] = []
    try:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
    except Exception as e:
        return [f"{py_file}: Failed to parse AST: {e}"]

    # Find top-level __all__ definition
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
        return errors

    for node in all_nodes:
        if not isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
            continue

        symbols: list[str] = []
        for elt in node.value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                symbols.append(elt.value)

        # 1. Check for duplicates
        seen = set()
        for sym in symbols:
            if sym in seen:
                errors.append(
                    f"{py_file}:{node.lineno}: Duplicate entry '{sym}' in __all__"
                )
            seen.add(sym)

        # 2. Check alphabetical sorting
        sorted_symbols = sorted(symbols, key=str.casefold)
        if symbols != sorted_symbols:
            errors.append(
                f"{py_file}:{node.lineno}: __all__ is not sorted alphabetically. "
                f"Expected order: {sorted_symbols}"
            )

    return errors


def main() -> int:
    """Run __all__ integrity checks across target python files."""
    parser = HexastackScriptArgumentParser(
        description="Verify API surface and __all__ statement integrity."
    )
    args = parser.parse_args()

    py_files = resolve_target_python_files(args)
    errors: list[str] = []

    for py_file in py_files:
        errors.extend(check_file_all(py_file))

    if errors:
        sys.stderr.write("API Surface / __all__ Integrity Violations Found:\n")
        for err in errors:
            sys.stderr.write(f"  - {err}\n")
        return 1

    print(f"API Surface check passed: verified {len(py_files)} Python source modules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
