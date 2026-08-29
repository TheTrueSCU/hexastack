"""Test Parity and Directory Integrity Checker for Hexastack."""

from __future__ import annotations

import os
from pathlib import Path

from hexastack_tools.utils.workspace import get_repo_root

_EXEMPT_SRC_FILES: set[str] = {
    "src/hexastack/__main__.py",
    "src/hexastack_cli/__main__.py",
}

_EXEMPT_TEST_FILES: set[str] = {
    "test_package.py",
}


def check_test_directories_inits(root_dir: Path) -> list[str]:
    """Ensure every sub-directory under packages/*/tests contains __init__.py."""
    errors: list[str] = []
    packages_dir = root_dir / "packages"
    if not packages_dir.exists():
        return errors

    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue
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
    """Check src files have matching unit tests."""
    errors: list[str] = []
    for src_file in src_dir.rglob("*.py"):
        if src_file.name == "__init__.py":
            continue
        rel_src = src_file.relative_to(src_dir)
        if any(str(rel_src).endswith(ex) for ex in _EXEMPT_SRC_FILES):
            continue

        test_parts = list(rel_src.parts[:-1]) + [f"test_{rel_src.name}"]
        expected_test = unit_tests_dir.joinpath(*test_parts)

        if not expected_test.is_file():
            errors.append(
                f"Missing unit test for {src_file.relative_to(root_dir)}: expected {expected_test.relative_to(root_dir)}"
            )
    return errors


def _check_package_test_symmetry(
    pkg: Path,
    root_dir: Path,
    src_dir: Path,
    unit_tests_dir: Path,
) -> list[str]:
    """Check unit test files have matching source modules."""
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


def check_src_to_test_symmetry(root_dir: Path) -> list[str]:
    """Ensure every src module has a matching unit test and vice versa."""
    errors: list[str] = []
    packages_dir = root_dir / "packages"
    if not packages_dir.exists():
        return errors

    for pkg in sorted(packages_dir.iterdir()):
        if not pkg.is_dir():
            continue

        src_dir = pkg / "src" / pkg.name
        unit_tests_dir = pkg / "tests" / "unit"

        if not src_dir.exists() or not unit_tests_dir.exists():
            continue

        errors.extend(
            _check_package_src_symmetry(pkg, root_dir, src_dir, unit_tests_dir)
        )
        errors.extend(
            _check_package_test_symmetry(pkg, root_dir, src_dir, unit_tests_dir)
        )

    return errors


def main() -> int:
    """CLI entrypoint for check-test-parity."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    root = get_repo_root()

    init_errors = check_test_directories_inits(root)
    symmetry_errors = check_src_to_test_symmetry(root)
    all_errors = init_errors + symmetry_errors

    if all_errors:
        table = Table(
            title="[bold red]❌ Test Parity & Directory Integrity Violations[/bold red]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Violation Type", width=24, style="bold red")
        table.add_column("Details")

        for err in init_errors:
            table.add_row("Missing __init__.py", err)
        for err in symmetry_errors:
            table.add_row("Asymmetry / Missing Test", err)

        console.print(table)
        return 1

    console.print(
        Panel(
            "[bold green]✅ All source modules mirror unit tests 1:1 and all test directories contain __init__.py.[/bold green]",
            border_style="green",
        )
    )
    return 0


__all__ = [
    "check_src_to_test_symmetry",
    "check_test_directories_inits",
    "main",
]
