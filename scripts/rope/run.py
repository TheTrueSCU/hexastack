"""Extended refactoring & AST sorting CLI for AI agents."""

import argparse
import ast
import sys
from pathlib import Path

from rope.base.project import Project
from rope.refactor.extract import ExtractMethod
from rope.refactor.move import create_move
from rope.refactor.rename import Rename


class MethodAlphabetizer(ast.NodeTransformer):
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        dunders, non_methods, methods = ([], [], [])
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name.startswith("__") and item.name.endswith("__"):
                    dunders.append(item)
                else:
                    methods.append(item)
            else:
                non_methods.append(item)

        methods.sort(key=lambda m: m.name.lower())
        node.body = non_methods + dunders + methods
        return node


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


def handle_extract_method(args):
    proj = Project(args.root)
    res = proj.get_resource(args.file)
    start, end = get_line_offsets(args.file, args.start_line, args.end_line)
    extractor = ExtractMethod(proj, res, start, end)
    proj.do(extractor.get_changes(args.name))
    proj.close()
    print(f"Extracted method '{args.name}'.")


def handle_move(args):
    """Move a function/class to another module and fix all project imports."""
    proj = Project(args.root)
    src_res = proj.get_resource(args.source_file)
    dest_res = proj.get_resource(args.dest_file)
    offset = get_offset(args.source_file, args.line, args.col)
    mover = create_move(proj, src_res, offset)
    changes = mover.get_changes(dest_res)
    proj.do(changes)
    proj.close()
    print(f"Moved symbol to '{args.dest_file}' and updated references.")


def handle_rename(args):
    proj = Project(args.root)
    res = proj.get_resource(args.file)
    offset = get_offset(args.file, args.line, args.col)
    renamer = Rename(proj, res, offset)
    proj.do(renamer.get_changes(args.new_name))
    proj.close()
    print(f"Renamed symbol to '{args.new_name}'.")


def handle_sort_methods(args):
    path = Path(args.file)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    transformer = MethodAlphabetizer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    path.write_text(ast.unparse(new_tree) + "\n", encoding="utf-8")
    print(f"Alphabetized methods in {args.file} (kept dunders and attributes intact).")


def main():
    parser = argparse.ArgumentParser(description="Deterministic Refactor Engine")
    parser.add_argument("--root", default=".")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_rename = subparsers.add_parser("rename")
    p_rename.add_argument("--file", type=Path, required=True)
    p_rename.add_argument("--line", type=int, required=True)
    p_rename.add_argument("--col", type=int, required=True)
    p_rename.add_argument("--new-name", required=True)

    p_ext = subparsers.add_parser("extract-method")
    p_ext.add_argument("--file", type=Path, required=True)
    p_ext.add_argument("--start-line", type=int, required=True)
    p_ext.add_argument("--end-line", type=int, required=True)
    p_ext.add_argument("--name", required=True)

    p_move = subparsers.add_parser("move")
    p_move.add_argument("--source-file", type=Path, required=True)
    p_move.add_argument("--line", type=int, required=True)
    p_move.add_argument("--col", type=int, required=True)
    p_move.add_argument("--dest-file", type=Path, required=True)

    p_sort = subparsers.add_parser("sort-methods")
    p_sort.add_argument("--file", type=Path, required=True)

    args = parser.parse_args()

    handlers = {
        "rename": handle_rename,
        "extract-method": handle_extract_method,
        "move": handle_move,
        "sort-methods": handle_sort_methods,
    }
    try:
        handlers[args.command](args)
    except Exception as e:
        sys.stderr.write(f"Operation failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
