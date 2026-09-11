"""Filesystem utilities for test directory integrity and 1:1 test parity auditing.

Notes/Architectural Intent:
    Pure filesystem inspection utilities verifying symmetry between packages/*/src
    and packages/*/tests without dependencies on higher-level framework layers.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = [
    "check_package_parity",
    "check_test_directories_inits",
]

_EXEMPT_SRC_FILES: set[str] = {
    "src/hexastack/__main__.py",
    "src/hexastack_cli/__main__.py",
}

_EXEMPT_TEST_FILES: set[str] = {
    "test_package.py",
}


def check_test_directories_inits(root_dir: Path) -> list[str]:
    """Ensure every sub-directory under packages/*/tests contains __init__.py.

    Args:
        root_dir: Directory containing packages/ directory or a package directory.

    Returns:
        List of missing __init__.py error descriptions.
    """
    errors: list[str] = []
    packages_dir = (
        root_dir / "packages" if (root_dir / "packages").is_dir() else root_dir
    )

    if packages_dir.name == "packages":
        pkg_dirs = [p for p in sorted(packages_dir.iterdir()) if p.is_dir()]
    else:
        pkg_dirs = [packages_dir]

    for pkg in pkg_dirs:
        tests_dir = pkg / "tests"
        if not tests_dir.exists():
            continue

        for dirpath, _, _ in os.walk(tests_dir):
            if "__pycache__" in dirpath or ".pytest_cache" in dirpath:
                continue
            if Path(dirpath) == tests_dir:
                continue
            init_file = Path(dirpath) / "__init__.py"
            if not init_file.exists():
                errors.append(f"Missing __init__.py in test directory: {dirpath}")

    return errors


def _check_package_src_symmetry(
    pkg: Path,
    root_dir: Path,
    src_dir: Path,
    unit_tests_dir: Path,
) -> list[str]:
    """Verify each source module in a package has a corresponding unit test."""
    errors: list[str] = []
    for src_file in src_dir.rglob("*.py"):
        rel_root = src_file.relative_to(root_dir)
        if str(rel_root) in _EXEMPT_SRC_FILES or src_file.name == "__init__.py":
            continue

        rel_src = src_file.relative_to(src_dir)
        test_filename = f"test_{src_file.name}"
        test_parts = list(rel_src.parts[:-1]) + [test_filename]
        expected_test = unit_tests_dir.joinpath(*test_parts)

        if not expected_test.is_file():
            errors.append(
                f"Missing unit test for {rel_root}: expected {expected_test.relative_to(root_dir)}"
            )
    return errors


def _check_package_test_symmetry(
    pkg: Path,
    root_dir: Path,
    src_dir: Path,
    unit_tests_dir: Path,
) -> list[str]:
    """Verify each unit test file corresponds to an existing source module."""
    errors: list[str] = []
    for test_file in unit_tests_dir.rglob("*.py"):
        if test_file.name == "__init__.py" or test_file.name in _EXEMPT_TEST_FILES:
            continue
        rel_test = test_file.relative_to(unit_tests_dir)
        if not test_file.name.startswith("test_"):
            continue

        src_filename = test_file.name.removeprefix("test_")
        src_parts = list(rel_test.parts[:-1]) + [src_filename]
        expected_src = src_dir.joinpath(*src_parts)

        if not expected_src.is_file():
            errors.append(
                f"Orphaned unit test {test_file.relative_to(root_dir)}: expected source {expected_src.relative_to(root_dir)}"
            )
    return errors


def check_package_parity(pkg_dir: Path, repo_root: Path) -> list[str]:
    """Audit test directory inits and 1:1 source-to-test symmetry for a package.

    Args:
        pkg_dir: Package directory.
        repo_root: Root path of repository.

    Returns:
        List of parity violation errors.
    """
    errors: list[str] = []
    errors.extend(check_test_directories_inits(pkg_dir))

    src_dir = pkg_dir / "src" / pkg_dir.name
    unit_tests_dir = pkg_dir / "tests" / "unit"

    if src_dir.exists() and unit_tests_dir.exists():
        errors.extend(
            _check_package_src_symmetry(pkg_dir, repo_root, src_dir, unit_tests_dir)
        )
        errors.extend(
            _check_package_test_symmetry(pkg_dir, repo_root, src_dir, unit_tests_dir)
        )

    return errors
