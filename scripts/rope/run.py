"""Extended refactoring & AST sorting CLI for AI agents."""

import argparse
import json
import sys
from pathlib import Path

import libcst as cst
from rope.base.project import Project
from rope.refactor.change_signature import ChangeSignature
from rope.refactor.extract import ExtractMethod, ExtractVariable
from rope.refactor.move import MoveModule, create_move
from rope.refactor.rename import Rename
from rope.refactor.usefunction import UseFunction


class FunctionAndMethodAlphabetizerCST(cst.CSTTransformer):
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

        methods.sort(key=lambda m: m.name.value.lower())
        new_body = non_methods + dunders + methods
        return updated_node.with_deep_changes(
            updated_node.body,
            body=tuple(new_body),
        )

    def leave_Module(
        self, original_node: cst.Module, updated_node: cst.Module
    ) -> cst.Module:
        top_matter = []  # Imports, module docstrings, type aliases, top-level assignments/classes
        functions = []  # Top-level standalone functions
        bottom_matter = []  # if __name__ == '__main__': blocks

        for stmt in updated_node.body:
            if isinstance(stmt, cst.FunctionDef):
                functions.append(stmt)
            elif self._is_main_guard(stmt):
                bottom_matter.append(stmt)
            else:
                top_matter.append(stmt)

        # Sort top-level functions alphabetically
        functions.sort(key=lambda f: f.name.value.lower())

        new_body = top_matter + functions + bottom_matter
        return updated_node.with_changes(body=tuple(new_body))


def get_line_offsets(filepath: Path, start_line: int, end_line: int) -> tuple[int, int]:
    with filepath.open(encoding="utf-8", mode="r") as f:
        lines = f.readlines()

    start_offset = sum(len(lines[i]) for i in range(start_line - 1))
    end_offset = sum(len(lines[i]) for i in range(end_line))
    return (start_offset, end_offset)


def get_offset(filepath: Path, line: int, col: int) -> int:
    with filepath.open(encoding="utf-8", mode="r") as f:
        lines = f.readlines()

    return sum(len(lines[i]) for i in range(line - 1)) + (col - 1)


def handle_change_signature(args):
    """
    Reorder, add, or remove parameters.
    --order expects comma-separated old param indices in new order (e.g. '1,0')
    --removals expects comma-separated param indices to drop (e.g. '2')
    --additions expects JSON array: '[{"index": 2, "name": "timeout", "default": "30"}]'
    """
    proj = Project(args.root)
    res = proj.get_resource(args.file)
    offset = get_offset(args.file, args.line, args.col)

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

    proj.do(changer.get_changes(normalizer))
    proj.close()
    print(
        f"Updated signature for function at {args.file}:{args.line}:{args.col} across project."
    )


def handle_extract_method(args):
    proj = Project(args.root)
    res = proj.get_resource(args.file)
    start, end = get_line_offsets(args.file, args.start_line, args.end_line)
    extractor = ExtractMethod(proj, res, start, end)
    proj.do(extractor.get_changes(args.name))
    proj.close()
    print(
        f"Extracted lines {args.start_line}-{args.end_line} into method '{args.name}'."
    )


def handle_extract_var(args):
    proj = Project(args.root)
    res = proj.get_resource(args.file)
    start = get_offset(args.file, args.start_line, args.start_col)
    end = get_offset(args.file, args.end_line, args.end_col)
    extractor = ExtractVariable(proj, res, start, end)
    proj.do(extractor.get_changes(args.name))
    proj.close()
    print(f"Extracted expression into variable '{args.name}'.")


def handle_move_module(args):
    """Move module/package to another folder and optionally rename it."""
    proj = Project(args.root)
    res = proj.get_resource(args.source_path)
    dest_folder = proj.get_resource(args.dest_folder)

    # 1. Move module into destination folder
    mover = MoveModule(proj, res)
    proj.do(mover.get_changes(dest_folder))

    # 2. If a new name is specified, rename the moved resource
    if args.new_name:
        dest_path = Path(args.dest_folder) / Path(args.source_path).name
        moved_res = proj.get_resource(str(dest_path))
        renamer = Rename(proj, moved_res)
        proj.do(renamer.get_changes(args.new_name))

    proj.close()
    print(
        f"Moved module '{args.source_path}' into '{args.dest_folder}' (renamed: {args.new_name or 'no'})."
    )


def handle_move_symbol(args):
    """Move a function/class to another module and update project imports."""
    proj = Project(args.root)
    src_res = proj.get_resource(args.source_file)
    dest_res = proj.get_resource(args.dest_file)
    offset = get_offset(args.source_file, args.line, args.col)

    mover = create_move(proj, src_res, offset)
    proj.do(mover.get_changes(dest_res))
    proj.close()
    print(f"Moved symbol to '{args.dest_file}' and updated all call sites/imports.")


def handle_rename(args):
    proj = Project(args.root)
    res = proj.get_resource(args.file)
    offset = get_offset(args.file, args.line, args.col)
    renamer = Rename(proj, res, offset)
    proj.do(renamer.get_changes(args.new_name))
    proj.close()
    print(f"Renamed symbol to '{args.new_name}'.")


def _handle_sort_methods(file_path, root_dir=None) -> bool:
    """Core logic to sort a file and emit user feedback."""
    path = Path(file_path)
    if root_dir and not path.is_absolute():
        path = root_dir / path

    if not path.is_file():
        sys.stderr.write(f"Target file does not exist: {path}\n")
        return False

    changed = sort_python_file(path)
    display_path = path.relative_to(root_dir) if root_dir else path
    if changed:
        print(f"Alphabetized methods & functions in: {display_path}")
    else:
        print(f"No ordering changes needed for: {display_path}")
    return changed


def handle_sort_methods(args) -> None:
    """CLI handler that unpacks argparse Namespace."""
    file_arg = getattr(args, "file", None) or getattr(args, "path", None)
    root = getattr(args, "root", None)
    root_path = Path(root) if root else None

    _handle_sort_methods(file_path=file_arg, root_dir=root_path)


def handle_use_function(args):
    """Find matching code logic project-wide and replace with calls to target function."""
    proj = Project(args.root)
    res = proj.get_resource(args.file)
    offset = get_offset(args.file, args.line, args.col)

    user = UseFunction(proj, res, offset)
    proj.do(user.get_changes())
    proj.close()
    print(
        f"Applied 'UseFunction' for symbol at {args.file}:{args.line}:{args.col} project-wide."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic Python Refactoring Engine for AI Agents"
    )
    parser.add_argument("--root", default=".", help="Project root (default: .)")
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
    p_sort = subparsers.add_parser("sort-methods", help="Alphabetize class methods")
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
        "move-symbol": handle_move_symbol,
        "move-module": handle_move_module,
        "rename": handle_rename,
        "sort-methods": handle_sort_methods,
        "use-function": handle_use_function,
    }

    try:
        handlers[args.command](args)
    except Exception as e:
        sys.stderr.write(f"Operation failed: {e}\n")
        sys.exit(1)


def sort_python_file(file_path: Path) -> bool:
    """Sorts functions/methods in a single Python file in place. Returns True if changed."""
    try:
        source_code = file_path.read_text(encoding="utf-8")
        module_cst = cst.parse_module(source_code)
        transformer = FunctionAndMethodAlphabetizerCST()
        modified_cst = module_cst.visit(transformer)

        if modified_cst.code != source_code:
            file_path.write_text(modified_cst.code, encoding="utf-8")
            return True
    except Exception as e:
        sys.stderr.write(f"Failed to alphabetize {file_path}: {e}\n")
    return False


if __name__ == "__main__":
    main()
