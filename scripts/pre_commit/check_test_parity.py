"""Test Parity and Directory Integrity Checker for Hexastack.

Notes/Architectural Intent:
    Guarantees structural 1:1 symmetry across Hexastack packages:
    1. Every module `src/<pkg>/a/b/c.py` has a corresponding unit test `tests/unit/a/b/test_c.py`.
    2. Every unit test `tests/unit/a/b/test_c.py` corresponds to a valid source file `src/<pkg>/a/b/c.py` (preventing orphaned tests).
    3. Every test directory under `packages/*/tests` contains an `__init__.py` file.
    4. Top-level package sanity tests (e.g. `test_package.py`) are exempted if appropriate.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Files/patterns that are exempted from 1:1 unit test mirroring
_EXEMPT_SRC_FILES: set[str] = {
    # Top-level entrypoint scripts or root exports
    "src/hexastack/__main__.py",
    "src/hexastack_cli/__main__.py",
}

_EXEMPT_TEST_FILES: set[str] = {
    # General package-level health check tests
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
            # Skip the root tests/ directory itself to avoid pytest importlib conftest collision
            if Path(dirpath) == tests_dir:
                continue
            init_file = Path(dirpath) / "__init__.py"
            if not init_file.exists():
                errors.append(f"Missing __init__.py in test directory: {dirpath}")

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
        src_dir = pkg / "src"
        tests_unit = pkg / "tests" / "unit"
        if not src_dir.exists():
            continue

        # Find the inner package directory (e.g. src/hexastack_core)
        inner_pkgs = [
            p for p in src_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
        ]
        if not inner_pkgs:
            continue
        inner_pkg = inner_pkgs[0]

        # 1. Check: src -> unit test
        for dirpath, _, filenames in os.walk(inner_pkg):
            rel_dir = Path(dirpath).relative_to(inner_pkg)
            for f in filenames:
                if not f.endswith(".py") or f.startswith("__"):
                    continue
                rel_src_path = Path(dirpath).relative_to(pkg) / f
                if str(rel_src_path) in _EXEMPT_SRC_FILES:
                    continue

                expected_test = tests_unit / rel_dir / f"test_{f}"
                if not expected_test.exists():
                    errors.append(
                        f"Missing unit test for {rel_src_path}: expected {expected_test.relative_to(pkg)}"
                    )

        # 2. Check: unit test -> src (orphan detection)
        if tests_unit.exists():
            for dirpath, _, filenames in os.walk(tests_unit):
                rel_dir = Path(dirpath).relative_to(tests_unit)
                for f in filenames:
                    if not f.startswith("test_") or not f.endswith(".py"):
                        continue
                    if f in _EXEMPT_TEST_FILES:
                        continue

                    src_filename = f[5:]  # Strip 'test_' prefix
                    expected_src = inner_pkg / rel_dir / src_filename
                    if not expected_src.exists():
                        test_path = Path(dirpath).relative_to(pkg) / f
                        errors.append(
                            f"Orphaned unit test {test_path}: expected source {expected_src.relative_to(pkg)}"
                        )

    return errors


def main() -> int:
    """Run test parity checks and exit with status code."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    root_dir = Path.cwd()
    errors: list[str] = []

    init_errors = check_test_directories_inits(root_dir)
    symmetry_errors = check_src_to_test_symmetry(root_dir)
    errors.extend(init_errors)
    errors.extend(symmetry_errors)

    if errors:
        table = Table(
            title="[bold red]❌ Test Parity & Directory Integrity Violations[/bold red]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Violation Type", style="bold red", width=30)
        table.add_column("Details", style="white", width=60)

        for err in init_errors:
            table.add_row("Missing __init__.py", err)
        for err in symmetry_errors:
            table.add_row("Asymmetry / Missing Test", err)

        console.print()
        console.print(table)
        console.print()
        return 1

    console.print(
        Panel.fit(
            "[bold green]✅ All source modules mirror unit tests 1:1 and all test directories contain __init__.py.[/bold green]",
            border_style="green",
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
