"""Pytest test runner and architecture contract generator commands."""

from __future__ import annotations

import argparse
import subprocess
import sys

import pytest

from hexastack_tools.utils.workspace import (
    VALID_PACKAGES,
    HexastackScriptArgumentParser,
    get_package_directories,
    get_package_directory,
    get_present_layers,
    get_repo_root,
    resolve_affected_packages,
)


def _get_git_changed_files(base_ref: str = "origin/main") -> list[str]:
    """Retrieve list of modified files compared against git base_ref."""
    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if files:
            return files
    except Exception:
        # Fall back to uncommitted local changes if diff against base_ref fails (e.g. shallow clone)
        pass

    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        # If git diff fails entirely (e.g. not in a git working tree), return empty list
        return []


def run_main() -> None:
    """CLI entrypoint for pytest-run."""
    parser = argparse.ArgumentParser(description="Run pytest test suite.")
    parser.add_argument(
        "-p", "--package", dest="packages", action="append", choices=VALID_PACKAGES
    )
    parser.add_argument("-A", "--affected", action="store_true")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    root = get_repo_root()
    test_paths: list[str] = []

    if args.packages:
        for p in args.packages:
            test_paths.append(str(get_package_directory(p, root) / "tests"))
    elif args.affected:
        changed = _get_git_changed_files()
        affected = resolve_affected_packages(changed, root)
        if affected:
            for p in affected:
                test_paths.append(str(get_package_directory(p, root) / "tests"))

    call_args = (test_paths or []) + (args.pytest_args or [])
    sys.exit(pytest.main(call_args))


def archon_generate_main() -> None:
    """CLI entrypoint for pytest-archon-generate."""
    parser = HexastackScriptArgumentParser(
        description="Generate pytest-archon boundary tests for packages."
    )
    args = parser.parse_args()

    root = get_repo_root()
    packages = (
        [get_package_directory(p, root) for p in args.packages]
        if args.packages
        else get_package_directories(root)
    )

    for pkg_path in packages:
        pkg_name = pkg_path.name
        if not get_present_layers(pkg_path):
            continue

        test_lines = [
            f'"""Hexagonal architecture boundary tests for {pkg_name}."""',
            "",
            "from hexastack_core.testing import assert_clean_architecture",
            "",
            "",
            f"def test_{pkg_name.replace('-', '_')}_clean_architecture():",
            f'    """Assert {pkg_name} strictly complies with Hexagonal layer isolation."""',
            f'    assert_clean_architecture("{pkg_name.replace("-", "_")}")',
            "",
        ]
        arch_dir = pkg_path / "tests" / "architecture"
        arch_dir.mkdir(parents=True, exist_ok=True)
        (arch_dir / "test_hexagonal_boundaries.py").write_text(
            "\n".join(test_lines).strip() + "\n"
        )


__all__ = [
    "archon_generate_main",
    "run_main",
]
