"""Extended refactoring & AST sorting CLI for AI agents using LibCST and Rope."""

from __future__ import annotations

from pathlib import Path

import libcst as cst
from rich.console import Console
from rich.panel import Panel

from hexastack_tools.utils.workspace import (
    HexastackScriptArgumentParser,
    get_repo_root,
    resolve_target_python_files,
)

console = Console()
ROOT_DIR = get_repo_root()


class FunctionAndMethodAlphabetizerCST(cst.CSTTransformer):
    """LibCST transformer to sort class methods and standalone functions alphabetically."""

    def _is_main_guard(self, stmt: cst.CSTNode) -> bool:
        """Check if statement is `if __name__ == '__main__':`."""
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
        """Alphabetize class methods while keeping class docstrings and dunder methods first."""
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
        """Alphabetize top-level standalone functions while preserving module headers and main guards."""
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


def sort_python_file(file_path: Path) -> bool:
    """Sort functions and class methods in a Python file alphabetically."""
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
    """CLI entrypoint for batch alphabetization."""
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
    """CLI entrypoint for general rope AST operations."""
    alphabetize_main()
    return 0


__all__ = [
    "alphabetize_main",
    "FunctionAndMethodAlphabetizerCST",
    "run_main",
    "sort_python_file",
]
