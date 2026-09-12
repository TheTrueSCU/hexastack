"""Import linter commands for contract generation and evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from hexastack_tools.adapters.presenters.dependency import create_dependency_presenter
from hexastack_tools.domain.dependencies import (
    GenerateImportLinterConfigCommand,
    RunImportLinterCommand,
)
from hexastack_tools.infra.bootstrap import create_governance_bus
from hexastack_tools.utils.import_linter import (
    build_import_linter_toml,
    update_pyproject_toml,
)
from hexastack_tools.utils.workspace import (
    HexastackScriptArgumentParser,
    ensure_tool_installed,
    get_package_directories,
    get_package_directory,
    get_packages_directory,
    get_repo_root,
)

__all__ = [
    "build_import_linter_toml",
    "generate_main",
    "run_main",
    "update_pyproject_toml",
]


def generate_main(argv: list[str] | None = None) -> None:
    """CLI entrypoint to generate import-linter contracts.

    Args:
        argv: Optional command-line arguments list.
    """
    parser = HexastackScriptArgumentParser(
        description="Generate [tool.importlinter] contracts in pyproject.toml."
    )
    args = parser.parse_args(argv)

    root = get_repo_root()
    if args.packages:
        packages = tuple(get_package_directory(p, root) for p in args.packages)
    else:
        packages = tuple(get_package_directories(root))

    bus = create_governance_bus()
    cmd = GenerateImportLinterConfigCommand(
        repo_root=root,
        packages=packages,
    )
    bus.dispatch(cmd)


def run_main(argv: list[str] | None = None) -> int:
    """CLI entrypoint to run import-linter per package.

    Args:
        argv: Optional command-line arguments list.

    Returns:
        Exit code (0 for success, non-zero for failures).
    """
    ensure_tool_installed(
        "importlinter", cli_command="lint-imports", extra_name="governance"
    )

    parser = argparse.ArgumentParser(description="Run import-linter per package.")
    parser.add_argument("files", nargs="*", help="Changed files passed by pre-commit")
    parser.add_argument(
        "--all", action="store_true", help="Run across all packages unconditionally"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json", "markdown"],
        default="table",
        help="Output presentation format (default: table).",
    )
    args = parser.parse_args(argv)

    packages_dir = get_packages_directory()
    all_packages = get_package_directories()

    if args.all or not args.files:
        targets = tuple(p for p in all_packages if (p / "pyproject.toml").is_file())
    else:
        target_list: list[Path] = []
        for file_str in args.files:
            try:
                rel = Path(file_str).relative_to(packages_dir)
                pkg_dir = packages_dir / rel.parts[0]
                if (
                    pkg_dir / "pyproject.toml"
                ).is_file() and pkg_dir not in target_list:
                    target_list.append(pkg_dir)
            except ValueError:
                continue
        targets = tuple(target_list)

    if not targets:
        return 0

    repo_root = get_repo_root()
    bus = create_governance_bus()
    presenter = create_dependency_presenter(args.format)

    cmd = RunImportLinterCommand(
        repo_root=repo_root,
        packages=targets,
        all_packages=args.all,
    )
    report = bus.dispatch(cmd)
    return presenter.present_import_linter(report)
