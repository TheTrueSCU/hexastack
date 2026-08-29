"""Pytest test runner and architecture contract generator commands."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

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


def _resolve_test_targets(
    packages: list[str] | None,
    affected: bool,
    unit_only: bool,
    properties_only: bool,
    root: Path,
) -> list[str]:
    """Resolve target test directory paths based on CLI flags."""
    if properties_only:
        sub_dir = "tests/properties"
    elif unit_only:
        sub_dir = "tests/unit"
    else:
        sub_dir = "tests"

    if packages:
        return [str(get_package_directory(p, root) / sub_dir) for p in packages]

    if affected:
        changed = _get_git_changed_files()
        affected_pkgs = resolve_affected_packages(changed, root)
        if affected_pkgs is not None:
            return [
                str(target)
                for p in affected_pkgs
                if (target := get_package_directory(p, root) / sub_dir).is_dir()
            ]
        # None indicates workspace-wide impact -> fall through to all packages

    return [
        str(target)
        for pkg_dir in get_package_directories(root)
        if (target := pkg_dir / sub_dir).is_dir()
    ]


def run_main() -> None:
    """CLI entrypoint for pytest-run."""
    parser = argparse.ArgumentParser(description="Run pytest test suite.")
    parser.add_argument(
        "-p", "--package", dest="packages", action="append", choices=VALID_PACKAGES
    )
    parser.add_argument("-A", "--affected", action="store_true")
    parser.add_argument("-U", "--unit", action="store_true")
    parser.add_argument("-P", "--properties", action="store_true")
    args, unknown = parser.parse_known_args()

    root = get_repo_root()
    test_paths = _resolve_test_targets(
        packages=args.packages,
        affected=args.affected,
        unit_only=args.unit,
        properties_only=args.properties,
        root=root,
    )

    call_args = test_paths + (unknown or [])
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
