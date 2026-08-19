"""Script to alphabetize functions and methods across packages or targeted directories.

Notes/Architectural Intent:
    Serves as the batch runner wrapper around rope's AST sorting capabilities.
    Processes full packages or subtrees while preserving module headers, class
    docstrings, dunders, and main guards.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts._common import VALID_PACKAGES, get_package_directory, get_repo_root
from scripts.rope.run import _handle_sort_methods, sort_python_file

ROOT_DIR = get_repo_root()


def collect_python_files(target_path: Path) -> list[Path]:
    """Recursively collect all .py files in a target directory or return the file itself.

    Args:
        target_path: Target directory or file Path.

    Returns:
        Sorted list of Path objects representing Python files.

    Raises:
        None.
    """
    if target_path.is_file() and target_path.suffix == ".py":
        return [target_path]
    if target_path.is_dir():
        return sorted(target_path.glob("**/*.py"))
    return []


def main() -> None:
    """CLI entrypoint for batch alphabetization."""
    parser = argparse.ArgumentParser(
        description="Alphabetize functions and class methods across packages deterministically."
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run alphabetization across all packages.",
    )
    parser.add_argument(
        "-p",
        "--package",
        default=None,
        help="Target package to alphabetize (e.g. core, cqrs, auth).",
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Explicit file or directory path to alphabetize (relative to CWD).",
    )

    args = parser.parse_args()

    target_files: list[Path] = []

    # 1. Explicit path (resolved against CWD)
    if args.path:
        explicit_path = Path(args.path).resolve()
        if explicit_path.is_file():
            _handle_sort_methods(file_path=explicit_path, root_dir=ROOT_DIR)
            return

        if explicit_path.is_dir():
            target_files.extend(collect_python_files(explicit_path))
        else:
            sys.stderr.write(f"Error: Path not found: {args.path}\n")
            sys.exit(1)

    # 2. Single package via common helper
    elif args.package:
        if args.package not in VALID_PACKAGES:
            sys.stderr.write(
                f"Error: Unknown package '{args.package}'. Valid options: {', '.join(VALID_PACKAGES)}\n"
            )
            sys.exit(1)

        pkg_dir = get_package_directory(args.package)
        target_files.extend(collect_python_files(pkg_dir))

    # 3. All packages across the repo
    elif args.all:
        for pkg in VALID_PACKAGES:
            pkg_dir = get_package_directory(pkg)
            target_files.extend(collect_python_files(pkg_dir))

    else:
        parser.print_help()
        sys.exit(1)

    if not target_files:
        print("No Python files found matching the criteria.")
        return

    # Process all collected files
    modified_count = 0
    for file_path in target_files:
        if sort_python_file(file_path):
            modified_count += 1
            print(f"Alphabetized: {file_path.relative_to(ROOT_DIR)}")

    print(f"\nDone. Processed {len(target_files)} file(s), {modified_count} modified.")


if __name__ == "__main__":
    main()
