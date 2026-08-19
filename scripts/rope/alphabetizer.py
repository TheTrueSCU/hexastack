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
    parser = HexastackScriptArgumentParser(
        description="Alphabetize functions and class methods across packages deterministically."
    )
    args = parser.parse_args()

    py_files = resolve_target_python_files(args)
    if not py_files:
        print("No Python files found matching the criteria.")
        return

    # Process all collected files
    modified_count = 0
    for file_path in py_files:
        if sort_python_file(file_path):
            modified_count += 1
            print(f"Alphabetized: {file_path.relative_to(ROOT_DIR)}")

    print(f"\nDone. Processed {len(py_files)} file(s), {modified_count} modified.")


if __name__ == "__main__":
    main()
