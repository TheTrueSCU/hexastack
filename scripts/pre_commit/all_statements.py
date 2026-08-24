"""API Surface & __all__ integrity checker and formatter for Hexastack codebase.

Notes/Architectural Intent:
    Two entrypoints share a single AST analysis pass, mirroring ruff's check/fix split:
    - ``main_check`` (check-api-surface): validates __all__ for duplicates and sort order;
      exits non-zero on any violation. Read-only.
    - ``main_fix`` (format-all-statements): rewrites __all__ in-place to be
      deduplicated and alphabetically sorted. Only rewrites List/Tuple nodes; ast.Set
      nodes are left untouched because set literals have no meaningful canonical order
      in source.
    Supports package, path, and all options via shared HexastackScriptArgumentParser.
"""

import ast
import sys
from pathlib import Path

from scripts._common import (
    HexastackScriptArgumentParser,
    resolve_target_python_files,
)

# ---------------------------------------------------------------------------
# Shared AST helpers
# ---------------------------------------------------------------------------


def _find_all_nodes(tree: ast.Module) -> list[ast.Assign]:
    """Return top-level ``__all__`` assignment nodes from a parsed module.

    Args:
        tree: A parsed AST module.

    Returns:
        A list of ``ast.Assign`` nodes whose targets include ``__all__``.

    Notes/Architectural Intent:
        Only top-level assignments are considered; ``__all__`` inside functions
        or classes is not a recognised Python convention.
    """
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
    """Extract string literal elements from an ``__all__`` assignment node.

    Args:
        node: An ``ast.Assign`` node whose value is a List, Tuple, or Set.

    Returns:
        Ordered list of string symbol names found in the node value.

    Notes/Architectural Intent:
        Non-string-literal elements (e.g. splat expressions) are silently skipped
        so that partially dynamic ``__all__`` definitions don't produce false errors.
    """
    if not isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
        return []
    return [
        elt.value
        for elt in node.value.elts
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
    ]


# ---------------------------------------------------------------------------
# Check mode
# ---------------------------------------------------------------------------


def check_file_all(py_file: Path) -> list[str]:
    """Check ``__all__`` declaration in a Python file via AST analysis.

    Args:
        py_file: Path to the Python source file to check.

    Returns:
        A list of human-readable error strings; empty if the file is clean.

    Raises:
        No exceptions are raised; parse failures are reported as error strings.

    Notes/Architectural Intent:
        Validates two invariants: no duplicate entries and case-insensitive
        alphabetical sort order. Symbol existence checks (declared-but-missing
        names) are intentionally deferred to a future enhancement.
    """
    errors: list[str] = []
    try:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))
    except Exception as e:
        return [f"{py_file}: Failed to parse AST: {e}"]

    for node in _find_all_nodes(tree):
        symbols = _extract_symbols(node)
        if not symbols:
            continue

        # 1. Check for duplicates
        seen: set[str] = set()
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


def main_check() -> int:
    """Run __all__ integrity checks across target Python files.

    Returns:
        Exit code: 0 on success, 1 if any violations are found.

    Notes/Architectural Intent:
        Intended as the ``check-all-statements`` console script entrypoint.
        Mirrors ruff's ``check`` mode: read-only, non-zero exit on violations.
    """
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


# ---------------------------------------------------------------------------
# Fix mode
# ---------------------------------------------------------------------------


def fix_file_all(py_file: Path) -> bool:
    """Alphabetize and deduplicate ``__all__`` in a Python source file in-place.

    Args:
        py_file: Path to the Python source file to rewrite.

    Returns:
        ``True`` if the file was modified, ``False`` otherwise.

    Notes/Architectural Intent:
        Only List and Tuple ``__all__`` nodes are rewritten; ``ast.Set`` literals
        are skipped because they have no meaningful canonical source order.
        Uses ``ast.get_source_segment`` for a surgical replacement rather than
        pretty-printing the whole file, so surrounding formatting is preserved.
    """
    content = py_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(content, filename=str(py_file))
    except Exception:
        return False

    modified = False
    new_content = content

    for node in _find_all_nodes(tree):
        # ast.Set excluded intentionally — see docstring
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


def main_fix() -> None:
    """Format ``__all__`` declarations in target Python files.

    Notes/Architectural Intent:
        Intended as the ``fix-all-statements`` console script entrypoint.
        Mirrors ruff's ``--fix`` mode: rewrites files in-place and reports a count.
        Always exits 0; use ``check-all-statements`` in CI to gate on violations.
    """
    parser = HexastackScriptArgumentParser(
        description="Format, alphabetize, and deduplicate __all__ statements."
    )
    args = parser.parse_args()

    py_files = resolve_target_python_files(args)
    formatted_count = sum(fix_file_all(f) for f in py_files)
    print(f"Formatted __all__ statements in {formatted_count} files.")


# ---------------------------------------------------------------------------
# Legacy shims — keep old ``main`` callable working if invoked directly
# ---------------------------------------------------------------------------

main = main_check


if __name__ == "__main__":
    sys.exit(main_check())
