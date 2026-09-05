"""Extended refactoring & AST sorting CLI for AI agents using LibCST and Rope."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import libcst as cst
from rich.console import Console
from rich.panel import Panel

from hexastack_tools.utils.workspace import (
    HexastackScriptArgumentParser,
    ensure_tool_installed,
    get_repo_root,
    resolve_target_python_files,
)

console = Console()
ROOT_DIR = get_repo_root()


class FunctionAndMethodAlphabetizerCST(cst.CSTTransformer):
    """LibCST transformer to sort class methods and standalone functions alphabetically."""

    def _is_main_guard(self, stmt: cst.CSTNode) -> bool:
        """Check if statement is `if __name__ == '__main__':`.

        Args:
            stmt: CST node statement to inspect.

        Returns:
            True if stmt matches main guard, False otherwise.
        """
        if not isinstance(stmt, cst.If):
            return False
        test = stmt.test
        if isinstance(test, cst.Comparison):
            left = getattr(test.left, "value", None)
            if left == "__name__":
                for comp in test.comparisons:
                    if getattr(comp.comparator, "value", "").strip("'\"") == "__main__":
                        return True
        return False

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        """Alphabetize class methods while keeping class docstrings and dunder methods first.

        Args:
            original_node: Original ClassDef CST node.
            updated_node: Updated ClassDef CST node.

        Returns:
            Alphabetized ClassDef CST node.
        """
        dunders = []
        non_methods = []
        methods = []

        for stmt in updated_node.body.body:
            if isinstance(stmt, cst.FunctionDef):
                name = stmt.name.value
                if name.startswith("__") and name.endswith("__"):
                    dunders.append(stmt)
                else:
                    methods.append(stmt)
            else:
                non_methods.append(stmt)

        sorted_methods = sorted(methods, key=lambda m: m.name.value.lower())
        new_body = non_methods + dunders + sorted_methods
        return updated_node.with_changes(
            body=updated_node.body.with_changes(body=new_body)
        )

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        """Alphabetize top-level standalone functions while preserving module headers and main guards.

        Args:
            original_node: Original Module CST node.
            updated_node: Updated Module CST node.

        Returns:
            Alphabetized Module CST node.
        """
        module_header = []
        functions = []
        trailing_statements = []
        collecting_header = True

        for stmt in updated_node.body:
            if isinstance(stmt, cst.FunctionDef):
                collecting_header = False
                functions.append(stmt)
            elif self._is_main_guard(stmt):
                collecting_header = False
                trailing_statements.append(stmt)
            elif collecting_header:
                module_header.append(stmt)
            else:
                trailing_statements.append(stmt)

        sorted_functions = sorted(functions, key=lambda f: f.name.value.lower())
        new_body = module_header + sorted_functions + trailing_statements
        return updated_node.with_changes(body=new_body)


def get_line_offsets(filepath: Path, start_line: int, end_line: int) -> tuple[int, int]:
    """Calculate character offset ranges from 1-based line numbers.

    Args:
        filepath: Path to the target Python file.
        start_line: 1-based starting line number.
        end_line: 1-based ending line number.

    Returns:
        Tuple of (start_char_offset, end_char_offset).
    """
    with filepath.open(encoding="utf-8", mode="r") as f:
        lines = f.readlines()

    start_offset = sum(len(lines[i]) for i in range(start_line - 1))
    end_offset = sum(len(lines[i]) for i in range(end_line))
    return (start_offset, end_offset)


def get_offset(filepath: Path, line: int, col: int) -> int:
    """Calculate character offset from 1-based line and 1-based column numbers.

    Args:
        filepath: Path to the target Python file.
        line: 1-based line number.
        col: 1-based column number.

    Returns:
        0-based character offset within the file.
    """
    with filepath.open(encoding="utf-8", mode="r") as f:
        lines = f.readlines()

    return sum(len(lines[i]) for i in range(line - 1)) + (col - 1)


def _apply_changes(proj: Any, changes: Any, dry_run: bool = False) -> None:
    """Apply or preview a set of Rope refactoring changes.

    Args:
        proj: Active Rope Project instance.
        changes: Rope ChangeSet or Change object.
        dry_run: If True, print changes without modifying disk.
    """
    if dry_run:
        console.print(
            "\n[bold yellow]--- Dry Run Refactoring Preview ---[/bold yellow]"
        )
        console.print(changes.get_description() or "No changes produced.")
        console.print(
            "[bold yellow]-----------------------------------[/bold yellow]\n"
        )
    else:
        proj.do(changes)


def handle_change_signature(args: argparse.Namespace) -> None:
    """Reorder, add, or remove parameters across call sites.

    Args:
        args: Parsed CLI namespace.
    """
    from rope.base.project import Project
    from rope.refactor.change_signature import ChangeSignature

    proj = Project(args.root)
    try:
        res = proj.get_resource(args.file)
        offset = get_offset(Path(args.file), args.line, args.col)

        changer = ChangeSignature(proj, res, offset)
        normalizer = changer.get_args()

        if args.removals:
            for idx in sorted(
                [int(x.strip()) for x in args.removals.split(",")], reverse=True
            ):
                normalizer.remove(idx)

        if args.order:
            new_order = [int(x.strip()) for x in args.order.split(",")]
            normalizer.reorder(new_order)

        if args.additions:
            adds = json.loads(args.additions)
            for add in adds:
                normalizer.add(
                    index=add["index"],
                    name=add["name"],
                    default=add.get("default", None),
                    value=add.get("value", None),
                )

        changes = changer.get_changes(normalizer)
        _apply_changes(proj, changes, getattr(args, "dry_run", False))
        console.print(
            f"[green]✓ Updated signature for function at {args.file}:{args.line}:{args.col} across project.[/green]"
        )
    finally:
        proj.close()


def handle_extract_method(args: argparse.Namespace) -> None:
    """Extract line range into a separate method/function.

    Args:
        args: Parsed CLI namespace.
    """
    from rope.base.project import Project
    from rope.refactor.extract import ExtractMethod

    proj = Project(args.root)
    try:
        res = proj.get_resource(args.file)
        start, end = get_line_offsets(Path(args.file), args.start_line, args.end_line)
        extractor = ExtractMethod(proj, res, start, end)
        changes = extractor.get_changes(args.name)
        _apply_changes(proj, changes, getattr(args, "dry_run", False))
        console.print(
            f"[green]✓ Extracted lines {args.start_line}-{args.end_line} into method '{args.name}'.[/green]"
        )
    finally:
        proj.close()


def handle_extract_var(args: argparse.Namespace) -> None:
    """Extract expression offset range into a variable.

    Args:
        args: Parsed CLI namespace.
    """
    from rope.base.project import Project
    from rope.refactor.extract import ExtractVariable

    proj = Project(args.root)
    try:
        res = proj.get_resource(args.file)
        start = get_offset(Path(args.file), args.start_line, args.start_col)
        end = get_offset(Path(args.file), args.end_line, args.end_col)
        extractor = ExtractVariable(proj, res, start, end)
        changes = extractor.get_changes(args.name)
        _apply_changes(proj, changes, getattr(args, "dry_run", False))
        console.print(
            f"[green]✓ Extracted expression into variable '{args.name}'.[/green]"
        )
    finally:
        proj.close()


def handle_inline(args: argparse.Namespace) -> None:
    """Inline a variable, method, or function project-wide or in current file.

    Args:
        args: Parsed CLI namespace.
    """
    from rope.base.project import Project
    from rope.refactor.inline import create_inline

    proj = Project(args.root)
    try:
        res = proj.get_resource(args.file)
        offset = get_offset(Path(args.file), args.line, args.col)
        inliner = create_inline(proj, res, offset)
        changes = inliner.get_changes()
        _apply_changes(proj, changes, getattr(args, "dry_run", False))
        console.print(
            f"[green]✓ Inlined symbol at {args.file}:{args.line}:{args.col} successfully.[/green]"
        )
    finally:
        proj.close()


def handle_find_occurrences(args: argparse.Namespace) -> None:
    """Find all semantic occurrences of a symbol across the project.

    Args:
        args: Parsed CLI namespace.
    """
    from rope.base import evaluate, worder
    from rope.base.project import Project
    from rope.refactor.occurrences import create_finder

    proj = Project(args.root)
    try:
        res = proj.get_resource(args.file)
        offset = get_offset(Path(args.file), args.line, args.col)
        name = worder.Worder(res.read()).get_word_at(offset)
        pyname = evaluate.eval_location(res, offset)

        if pyname is None:
            console.print(
                f"[yellow]No semantic symbol resolved at {args.file}:{args.line}:{args.col}.[/yellow]"
            )
            return

        finder = create_finder(proj, name, pyname)
        occurrences = list(finder.find_occurrences())

        console.print(
            f"\n[bold cyan]Found {len(occurrences)} occurrence(s) for symbol '{name}' ({args.file}:{args.line}:{args.col}):[/bold cyan]"
        )
        for occ in occurrences:
            res_path = occ.resource.path if occ.resource else args.file
            lineno = occ.lineno if hasattr(occ, "lineno") else "unknown"
            console.print(f"  {res_path}:{lineno} (offset: {occ.offset})")
        console.print()
    finally:
        proj.close()


def handle_move_module(args: argparse.Namespace) -> None:
    """Move module/package to another folder and optionally rename it.

    Args:
        args: Parsed CLI namespace.
    """
    from rope.base.project import Project
    from rope.refactor.move import MoveModule
    from rope.refactor.rename import Rename

    proj = Project(args.root)
    try:
        res = proj.get_resource(args.source_path)
        dest_folder = proj.get_resource(args.dest_folder)

        mover = MoveModule(proj, res)
        changes = mover.get_changes(dest_folder)
        _apply_changes(proj, changes, getattr(args, "dry_run", False))

        if args.new_name and not getattr(args, "dry_run", False):
            dest_path = Path(args.dest_folder) / Path(args.source_path).name
            moved_res = proj.get_resource(str(dest_path))
            renamer = Rename(proj, moved_res)
            proj.do(renamer.get_changes(args.new_name))

        console.print(
            f"[green]✓ Moved module '{args.source_path}' into '{args.dest_folder}' (renamed: {args.new_name or 'no'}).[/green]"
        )
    finally:
        proj.close()


def handle_move_symbol(args: argparse.Namespace) -> None:
    """Move a function/class to another module and update project imports.

    Args:
        args: Parsed CLI namespace.
    """
    from rope.base.project import Project
    from rope.refactor.move import create_move

    proj = Project(args.root)
    try:
        src_res = proj.get_resource(args.source_file)
        dest_res = proj.get_resource(args.dest_file)
        offset = get_offset(Path(args.source_file), args.line, args.col)

        mover = create_move(proj, src_res, offset)
        changes = mover.get_changes(dest_res)
        _apply_changes(proj, changes, getattr(args, "dry_run", False))
        console.print(
            f"[green]✓ Moved symbol to '{args.dest_file}' and updated all call sites/imports.[/green]"
        )
    finally:
        proj.close()


def handle_rename(args: argparse.Namespace) -> None:
    """Rename a symbol project-wide.

    Args:
        args: Parsed CLI namespace.
    """
    from rope.base.project import Project
    from rope.refactor.rename import Rename

    proj = Project(args.root)
    try:
        res = proj.get_resource(args.file)
        offset = get_offset(Path(args.file), args.line, args.col)
        renamer = Rename(proj, res, offset)
        changes = renamer.get_changes(args.new_name)
        _apply_changes(proj, changes, getattr(args, "dry_run", False))
        console.print(f"[green]✓ Renamed symbol to '{args.new_name}'.[/green]")
    finally:
        proj.close()


def handle_use_function(args: argparse.Namespace) -> None:
    """Find matching code logic project-wide and replace with calls to target function.

    Args:
        args: Parsed CLI namespace.
    """
    from rope.base.project import Project
    from rope.refactor.usefunction import UseFunction

    proj = Project(args.root)
    try:
        res = proj.get_resource(args.file)
        offset = get_offset(Path(args.file), args.line, args.col)

        user = UseFunction(proj, res, offset)
        changes = user.get_changes()
        _apply_changes(proj, changes, getattr(args, "dry_run", False))
        console.print(
            f"[green]✓ Applied 'UseFunction' for symbol at {args.file}:{args.line}:{args.col} project-wide.[/green]"
        )
    finally:
        proj.close()


def sort_python_file(file_path: Path) -> bool:
    """Sort functions and class methods in a Python file alphabetically.

    Args:
        file_path: Path to target Python file.

    Returns:
        True if file content was changed, False otherwise.
    """
    try:
        source_code = file_path.read_text(encoding="utf-8")
        tree = cst.parse_module(source_code)
        transformer = FunctionAndMethodAlphabetizerCST()
        modified_tree = tree.visit(transformer)
        if modified_tree.code != source_code:
            file_path.write_text(modified_tree.code, encoding="utf-8")
            return True
        return False
    except Exception:
        return False


def alphabetize_main() -> None:
    """CLI entrypoint for batch alphabetization.

    Notes/Architectural Intent:
        Alphabetizes standalone functions and class methods across files.
    """
    ensure_tool_installed("libcst", extra_name="rope")

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

    modified_count = 0
    for file_path in py_files:
        if sort_python_file(file_path):
            modified_count += 1
            console.print(
                f"  [cyan]Alphabetized:[/cyan] {file_path.relative_to(ROOT_DIR)}"
            )

    console.print(
        Panel.fit(
            f"[bold green]✨ Alphabetization complete: Processed {len(py_files)} file(s), {modified_count} modified.[/bold green]",
            border_style="green",
        )
    )


def run_main() -> int:
    """CLI entrypoint for deterministic rope refactoring commands.

    Returns:
        Process exit code.

    Notes/Architectural Intent:
        Dispatches precise AST refactoring operations (rename, extract, move, etc.).
    """
    ensure_tool_installed("rope", extra_name="rope")

    parser = argparse.ArgumentParser(
        description="Deterministic Python Refactoring Engine for AI Agents"
    )
    parser.add_argument("--root", default=".", help="Project root (default: .)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying source files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # change-signature
    p_cs = subparsers.add_parser(
        "change-signature", help="Change arguments on a function project-wide"
    )
    p_cs.add_argument("--file", required=True)
    p_cs.add_argument("--line", type=int, required=True)
    p_cs.add_argument("--col", type=int, required=True)
    p_cs.add_argument("--order", help="Reorder 0-based indices, e.g. '1,0'")
    p_cs.add_argument("--removals", help="Indices to remove, e.g. '2'")
    p_cs.add_argument(
        "--additions",
        help='JSON list, e.g. \'[{"index": 2, "name": "flag", "default": "False"}]\'',
    )

    # extract-method
    p_em = subparsers.add_parser("extract-method", help="Extract code block to method")
    p_em.add_argument("--file", required=True)
    p_em.add_argument("--start-line", type=int, required=True)
    p_em.add_argument("--end-line", type=int, required=True)
    p_em.add_argument("--name", required=True)

    # extract-var
    p_ev = subparsers.add_parser("extract-var", help="Extract expression to variable")
    p_ev.add_argument("--file", required=True)
    p_ev.add_argument("--start-line", type=int, required=True)
    p_ev.add_argument("--start-col", type=int, required=True)
    p_ev.add_argument("--end-line", type=int, required=True)
    p_ev.add_argument("--end-col", type=int, required=True)
    p_ev.add_argument("--name", required=True)

    # find-occurrences
    p_fo = subparsers.add_parser(
        "find-occurrences", help="Find all semantic occurrences of a symbol"
    )
    p_fo.add_argument("--file", required=True)
    p_fo.add_argument("--line", type=int, required=True)
    p_fo.add_argument("--col", type=int, required=True)

    # inline
    p_inl = subparsers.add_parser(
        "inline", help="Inline variable, method, or function project-wide"
    )
    p_inl.add_argument("--file", required=True)
    p_inl.add_argument("--line", type=int, required=True)
    p_inl.add_argument("--col", type=int, required=True)

    # move-module
    p_mm = subparsers.add_parser(
        "move-module", help="Move module/package to another folder"
    )
    p_mm.add_argument("--source-path", required=True, help="Module file or package dir")
    p_mm.add_argument("--dest-folder", required=True, help="Destination directory")
    p_mm.add_argument("--new-name", default=None, help="Optional rename for module")

    # move-symbol
    p_ms = subparsers.add_parser(
        "move-symbol", help="Move function/class to another file"
    )
    p_ms.add_argument("--source-file", required=True)
    p_ms.add_argument("--line", type=int, required=True)
    p_ms.add_argument("--col", type=int, required=True)
    p_ms.add_argument("--dest-file", required=True)

    # rename
    p_ren = subparsers.add_parser("rename", help="Rename a symbol project-wide")
    p_ren.add_argument("--file", required=True)
    p_ren.add_argument("--line", type=int, required=True)
    p_ren.add_argument("--col", type=int, required=True)
    p_ren.add_argument("--new-name", required=True)

    # sort-methods
    p_sort = subparsers.add_parser(
        "sort-methods", help="Alphabetize class methods in a file"
    )
    p_sort.add_argument("--file", required=True)

    # use-function
    p_uf = subparsers.add_parser(
        "use-function", help="Replace duplicated logic with calls to this function"
    )
    p_uf.add_argument("--file", required=True)
    p_uf.add_argument("--line", type=int, required=True)
    p_uf.add_argument("--col", type=int, required=True)

    args = parser.parse_args()

    handlers = {
        "change-signature": handle_change_signature,
        "extract-method": handle_extract_method,
        "extract-var": handle_extract_var,
        "find-occurrences": handle_find_occurrences,
        "inline": handle_inline,
        "move-symbol": handle_move_symbol,
        "move-module": handle_move_module,
        "rename": handle_rename,
        "sort-methods": lambda a: _handle_sort_methods(
            a.file, Path(a.root) if a.root else None
        ),
        "use-function": handle_use_function,
    }

    try:
        handlers[args.command](args)
        return 0
    except Exception as e:
        sys.stderr.write(f"Operation failed: {e}\n")
        return 1


def _handle_sort_methods(file_path: str | Path, root_dir: Path | None = None) -> bool:
    """Core logic to sort a file and emit user feedback.

    Args:
        file_path: String or Path to the target Python file.
        root_dir: Optional root directory Path for relative display.

    Returns:
        True if the file was modified, False otherwise.
    """
    path = Path(file_path)
    if root_dir and not path.is_absolute():
        path = root_dir / path

    if not path.is_file():
        sys.stderr.write(f"Target file does not exist: {path}\n")
        return False

    changed = sort_python_file(path)
    display_path = path.relative_to(root_dir) if root_dir else path
    if changed:
        console.print(
            f"[green]✓ Alphabetized methods & functions in: {display_path}[/green]"
        )
    else:
        console.print(f"[dim]No ordering changes needed for: {display_path}[/dim]")
    return changed


__all__ = [
    "alphabetize_main",
    "FunctionAndMethodAlphabetizerCST",
    "get_line_offsets",
    "get_offset",
    "handle_change_signature",
    "handle_extract_method",
    "handle_extract_var",
    "handle_find_occurrences",
    "handle_inline",
    "handle_move_module",
    "handle_move_symbol",
    "handle_rename",
    "handle_use_function",
    "run_main",
    "sort_python_file",
]
