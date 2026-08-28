"""Mutation testing runner script for Hexastack packages using mutmut v2.

Notes/Architectural Intent:
    Automates scoped mutation testing runs across packages or paths, and provides
    selective cache eviction for individual packages to avoid wiping out workspace-wide
    mutation results.

Usage:
    # Run a single package
    uv run mutmut-run --package ai

    # Clear cache for a package and rerun fresh
    uv run mutmut-run --package ai --fresh

    # Clear cache only without running
    uv run mutmut-run --package ai --clear-cache

    # Run all packages sequentially
    uv run mutmut-run --all
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys

from scripts._common import VALID_PACKAGES, get_repo_root

ROOT_DIR = get_repo_root()
CACHE_FILE = ROOT_DIR / ".mutmut-cache"


def clear_package_cache(package: str) -> int:
    """Selectively delete cached mutants for a specific package from SQLite cache.

    Args:
        package: Short package name (e.g. 'ai', 'db', 'fastapi').

    Returns:
        Number of mutant rows deleted.

    Notes/Architectural Intent:
        Directly clears rows in Mutant, Line, and SourceFile for files matching
        the package path, preserving all other packages' mutation results.
    """
    if not CACHE_FILE.exists():
        return 0

    pkg_clean = package.removeprefix("hexastack_").removeprefix("hexastack-")
    pattern = f"%hexastack_{pkg_clean}%"

    con = sqlite3.connect(CACHE_FILE)
    try:
        cur = con.cursor()
        # Find matching source file IDs
        file_rows = cur.execute(
            "SELECT id FROM SourceFile WHERE filename LIKE ?", (pattern,)
        ).fetchall()
        if not file_rows:
            return 0

        file_ids = [row[0] for row in file_rows]
        placeholders = ",".join("?" * len(file_ids))

        # Find matching line IDs
        line_rows = cur.execute(
            f"SELECT id FROM Line WHERE sourcefile IN ({placeholders})",  # noqa: S608
            file_ids,
        ).fetchall()
        line_ids = [row[0] for row in line_rows]

        deleted_mutants = 0
        if line_ids:
            line_placeholders = ",".join("?" * len(line_ids))
            cur.execute(
                f"DELETE FROM Mutant WHERE line IN ({line_placeholders})",  # noqa: S608
                line_ids,
            )
            deleted_mutants = cur.rowcount
            cur.execute(
                f"DELETE FROM Line WHERE id IN ({line_placeholders})",  # noqa: S608
                line_ids,
            )

        cur.execute(
            f"DELETE FROM SourceFile WHERE id IN ({placeholders})",  # noqa: S608
            file_ids,
        )
        con.commit()
        return deleted_mutants
    finally:
        con.close()


def run_command(cmd: list[str]) -> int:
    """Execute a shell command from project root directory.

    Args:
        cmd: List of command arguments.

    Returns:
        Exit code of the process.
    """
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT_DIR, check=False)
    return result.returncode


def run_mutation_test(
    package: str,
    path: str | None = None,
    fresh: bool = False,
) -> int:
    """Run mutmut against a designated Hexastack package.

    Args:
        package: Target package name.
        path: Optional explicit path override.
        fresh: If True, clears cached mutants for this package before running.

    Returns:
        Exit code from mutmut runner.
    """
    pkg_clean = package.removeprefix("hexastack_").removeprefix("hexastack-")
    if pkg_clean not in VALID_PACKAGES:
        print(
            f"Error: Unknown package '{package}'. Valid packages: {', '.join(VALID_PACKAGES)}"
        )
        return 1

    if fresh:
        deleted = clear_package_cache(pkg_clean)
        if deleted:
            print(f"Cleared {deleted} cached mutants for hexastack_{pkg_clean}.")

    pkg_dir = f"packages/hexastack_{pkg_clean}"
    if not (ROOT_DIR / pkg_dir).exists():
        pkg_dir = "packages/hexastack"

    src_path = path or f"{pkg_dir}/src/hexastack_{pkg_clean}"
    tests_path = f"{pkg_dir}/tests/unit"
    pytest_bin = str(ROOT_DIR / ".venv/bin/pytest")

    print("\n========================================================")
    print(f" Starting Mutation Testing: hexastack-{pkg_clean}")
    print(f" Source:    {src_path}")
    print(f" Tests Dir: {tests_path}")
    print(f" Pytest:    {pytest_bin}")
    print("========================================================\n")

    cmd = [
        "uv",
        "run",
        "mutmut",
        "run",
        f"--paths-to-mutate={src_path}",
        f"--tests-dir={tests_path}",
        f'--runner={pytest_bin} {tests_path} -n 0 -x -q --no-cov -o addopts=""',
    ]

    code = run_command(cmd)

    print("\n--- Mutmut Results ---")
    run_command(["uv", "run", "mutmut", "results"])
    return code


def run_all_mutation_tests(fresh: bool = False) -> int:
    """Run mutmut sequentially across all Hexastack packages.

    Args:
        fresh: If True, clears each package's cache before executing.

    Returns:
        0 if all packages pass with 0 survivors, 1 otherwise.
    """
    print("\n========================================================")
    print(f" Running Mutation Testing Across All {len(VALID_PACKAGES)} Packages")
    print("========================================================\n")

    results: dict[str, int] = {}
    for pkg in VALID_PACKAGES:
        print(f"\n>>> Running mutmut for hexastack-{pkg}...")
        code = run_mutation_test(pkg, fresh=fresh)
        results[pkg] = code

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    table = Table(
        title="[bold cyan]Mutation Testing Batch Summary[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Package", style="bold white", width=25)
    table.add_column("Status", width=30)
    table.add_column("Exit Code", justify="right", width=12)

    for pkg, code in results.items():
        if code == 0:
            status = "[bold green]PASSED[/bold green] (0 survivors)"
            exit_style = "green"
        else:
            status = "[bold red]SURVIVORS[/bold red]"
            exit_style = "red"
        table.add_row(
            f"hexastack-{pkg}", status, f"[{exit_style}]{code}[/{exit_style}]"
        )

    console.print()
    console.print(table)
    console.print()

    if all(c == 0 for c in results.values()):
        console.print(
            Panel.fit(
                "[bold green]✨ All mutated packages passed with zero surviving mutants![/bold green]",
                border_style="green",
            )
        )
        return 0
    console.print(
        Panel.fit(
            "[bold yellow]⚠️ Surviving mutants detected. Use 'uv run mutmut-inspect' to triage.[/bold yellow]",
            border_style="yellow",
        )
    )
    return 1


def show_mutant(mutant_id: str) -> int:
    """Display diff for a specific surviving mutant.

    Args:
        mutant_id: Numeric ID of the mutant.

    Returns:
        Process exit code.
    """
    return run_command(["uv", "run", "mutmut", "show", mutant_id])


def main() -> None:
    """Parse CLI arguments and dispatch mutation test runner."""
    parser = argparse.ArgumentParser(
        description="Hexastack Mutation Testing Runner (mutmut v2)"
    )
    parser.add_argument(
        "-p",
        "--package",
        default=None,
        help="Target package to mutate (e.g. core, cqrs, auth, ai, cli).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run mutation testing sequentially across all packages.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Clear cached mutants for the target package(s) before running.",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cached mutants for the target package without running tests.",
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Explicit file or directory path to mutate.",
    )
    parser.add_argument(
        "--show",
        default=None,
        help="Inspect a specific mutant diff by ID (e.g. --show 1).",
    )

    args = parser.parse_args()

    if args.show:
        sys.exit(show_mutant(args.show))

    if args.clear_cache:
        pkg = args.package or "core"
        deleted = clear_package_cache(pkg)
        print(f"Cleared {deleted} cached mutant(s) for hexastack_{pkg}.")
        sys.exit(0)

    if args.all or args.package == "all":
        sys.exit(run_all_mutation_tests(fresh=args.fresh))

    pkg = args.package or "core"
    sys.exit(run_mutation_test(pkg, args.path, fresh=args.fresh))


if __name__ == "__main__":
    main()
