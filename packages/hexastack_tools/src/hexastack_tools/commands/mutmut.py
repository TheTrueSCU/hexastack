"""Mutmut mutation testing runner and cache inspection commands."""

from __future__ import annotations

import argparse
import contextlib
import enum
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.utils.workspace import (
    VALID_PACKAGES,
    ensure_tool_installed,
    get_package_directories,
    get_package_directory,
    get_repo_root,
)

ROOT_DIR = get_repo_root()
CACHE_FILE = ROOT_DIR / ".mutmut-cache"
console = Console()


class MutantCategory(enum.StrEnum):
    """Classification category for surviving mutants based on triage severity."""

    CRITICAL = "CRITICAL"
    EQUIVALENT = "EQUIVALENT"
    IGNORABLE = "IGNORABLE"


def classify_mutant_line(line_str: str, filename: str) -> tuple[MutantCategory, str]:
    """Classify a surviving mutant based on syntactic and contextual heuristics.

    Args:
        line_str: Raw line of source code where mutation survived.
        filename: Path of the source file.

    Returns:
        Tuple of (Category, Rationale string).

    Notes/Architectural Intent:
        Categorizes surviving mutants into Critical, Equivalent, or Ignorable to
        focus developer effort on actionable logic and security defects.
    """
    # 1. Ignorable test harnesses & demo recordings
    if "/testing/" in filename or "/devtools/" in filename or "recorder.py" in filename:
        return MutantCategory.IGNORABLE, "Test harness / demo recorder"

    # 2. Ignorable logging & terminal UI print statements
    if re.search(r"\b(?:logger|log)\.(?:debug|info|trace|warning|error)\(", line_str):
        return MutantCategory.IGNORABLE, "Log statement format"
    if re.search(r"\b(?:typer\.echo|console\.print|print)\(", line_str):
        return MutantCategory.IGNORABLE, "CLI / Console output"

    # 3. Ignorable docstrings / help metadata
    if re.search(r"\b(?:help|description|summary|instructions)\s*=", line_str):
        return MutantCategory.IGNORABLE, "Doc / Help text"
    if re.search(r":\s*(?:bool|str|int|float|list|dict|set)[^=]*=\s*Field\(", line_str):
        return MutantCategory.IGNORABLE, "Pydantic Field metadata"

    # 4. Equivalent candidates (dict fallbacks, default kwargs, None defaults, dataclass metadata)
    if re.search(r"@dataclass\(", line_str):
        return MutantCategory.EQUIVALENT, "Dataclass decorator configuration"
    if re.search(r":\s*[^=]+=\s*None\b", line_str):
        return MutantCategory.EQUIVALENT, "Model / dataclass default None attribute"
    if re.search(r"\.get\([^,]+,\s*None\)", line_str):
        return MutantCategory.EQUIVALENT, "Dict fallback with None default"
    if re.search(r"=\s*None\s*\)", line_str) or re.search(r"=\s*None\s*,", line_str):
        return MutantCategory.EQUIVALENT, "Optional parameter None default"
    if re.search(r"\bcast\(", line_str):
        return MutantCategory.EQUIVALENT, "Type casting statement"

    # 5. Critical / Actionable (Branch conditions, error mapping, security, state changes)
    if re.search(r"\b(?:if|elif|while|return|raise|assert)\b", line_str):
        return MutantCategory.CRITICAL, "Control flow / branching / assertion"
    if re.search(
        r"\b(?:status|error|exception|retry|auth|token|security)\b",
        line_str,
        re.IGNORECASE,
    ):
        return MutantCategory.CRITICAL, "Domain status / security / error handling"
    if re.search(r"[+\-*/%<>=!&|^]", line_str):
        return MutantCategory.CRITICAL, "Arithmetic / Comparison / Logical operator"

    return MutantCategory.CRITICAL, "Domain execution logic"


def get_db_connection() -> sqlite3.Connection | None:
    """Connect to SQLite mutmut cache if it exists.

    Returns:
        Active sqlite3 Connection, or None if the cache does not exist.

    Notes/Architectural Intent:
        Connects to root .mutmut-cache file generated during mutmut execution.
    """
    if not CACHE_FILE.exists():
        console.print(f"[yellow]Cache file not found at {CACHE_FILE}[/yellow]")
        return None
    return sqlite3.connect(CACHE_FILE)


def show_summary(con: sqlite3.Connection) -> None:
    """Print high-level summary of surviving mutants by package with triage classification.

    Args:
        con: Active SQLite connection to .mutmut-cache.

    Notes/Architectural Intent:
        Queries surviving mutants and produces a rich formatted summary table broken
        down by package and mutant severity category.
    """
    cur = con.cursor()
    query = """
    SELECT m.id, sf.filename, l.line
    FROM Mutant m
    JOIN Line l ON m.line = l.id
    JOIN SourceFile sf ON l.sourcefile = sf.id
    WHERE m.status IN ('bad_survived', 'bad_timeout')
    """
    rows = cur.execute(query).fetchall()
    if not rows:
        console.print("[green]✨ No surviving mutants found in cache![/green]")
        return

    package_stats: dict[str, dict[str, int]] = {}
    for _, filename, line_str in rows:
        match = re.search(r"packages/([^/]+)/", filename)
        pkg = match.group(1) if match else "hexastack"
        if pkg not in package_stats:
            package_stats[pkg] = {
                "total": 0,
                "critical": 0,
                "equivalent": 0,
                "ignorable": 0,
            }

        category, _ = classify_mutant_line(line_str.strip(), filename)
        package_stats[pkg]["total"] += 1
        package_stats[pkg][category.value.lower()] += 1

    table = Table(
        title="Surviving Mutants Triage Summary by Package", border_style="cyan"
    )
    table.add_column("Package", style="bold white", justify="left")
    table.add_column("Total", justify="right", style="cyan")
    table.add_column("🔴 Critical", justify="right", style="bold red")
    table.add_column("🟡 Equivalent", justify="right", style="yellow")
    table.add_column("🟢 Ignorable", justify="right", style="green")

    for pkg, stats in sorted(
        package_stats.items(), key=lambda x: x[1]["critical"], reverse=True
    ):
        table.add_row(
            pkg,
            str(stats["total"]),
            str(stats["critical"]),
            str(stats["equivalent"]),
            str(stats["ignorable"]),
        )

    console.print(table)


def show_file_mutants(
    con: sqlite3.Connection,
    pattern: str,
    limit: int = 25,
    actionable_only: bool = False,
    correlate_coverage: bool = False,
) -> None:
    """Print classified line details for surviving mutants matching a pattern.

    Args:
        con: Active SQLite connection to .mutmut-cache.
        pattern: Pattern matching target filename.
        limit: Maximum number of mutants to display.
        actionable_only: Whether to restrict display to critical mutants only.
        correlate_coverage: Whether to cross-reference .coverage to show tests executing each line.

    Notes/Architectural Intent:
        Lists individual mutant line details, snippets, diagnostic classification rationale,
        and optionally identifies test functions covering each mutant line.
    """
    from hexastack_tools.commands.coverage import get_tests_covering_line

    cur = con.cursor()
    query = """
    SELECT m.id, sf.filename, l.line_number, l.line
    FROM Mutant m
    JOIN Line l ON m.line = l.id
    JOIN SourceFile sf ON l.sourcefile = sf.id
    WHERE m.status IN ('bad_survived', 'bad_timeout')
    AND sf.filename LIKE ?
    ORDER BY sf.filename, l.line_number
    """
    rows = cur.execute(query, (f"%{pattern}%",)).fetchall()
    if not rows:
        console.print(f"[yellow]No surviving mutants matching '{pattern}'.[/yellow]")
        return

    filtered_rows = []
    for row in rows:
        cat, reason = classify_mutant_line(row[3].strip(), row[1])
        if actionable_only and cat != MutantCategory.CRITICAL:
            continue
        filtered_rows.append((row, cat, reason))

    title_suffix = " (Actionable Critical Only)" if actionable_only else ""
    console.print(
        f"\n[bold cyan]=== Surviving Mutants matching '{pattern}' ({len(filtered_rows)} total){title_suffix} ===[/bold cyan]\n"
    )

    for row, cat, reason in filtered_rows[:limit]:
        rel_path = row[1].replace(str(ROOT_DIR) + "/", "")
        line_str = row[3].strip()
        icon = (
            "🔴"
            if cat == MutantCategory.CRITICAL
            else ("🟡" if cat == MutantCategory.EQUIVALENT else "🟢")
        )
        console.print(
            f"  {icon} [bold]Mutant {row[0]:<4}[/bold] [{cat.value:<10}] | [dim]{rel_path}:{row[2]}[/dim]"
        )
        console.print(f"     [bold white]Code:[/bold white]   {line_str}")
        console.print(f"     [italic dim]Reason:[/italic dim] {reason}")

        if correlate_coverage:
            covering_tests = get_tests_covering_line(row[1], row[2])
            if covering_tests:
                console.print(
                    f"     [bold cyan]Covered by tests ({len(covering_tests)}):[/bold cyan]"
                )
                for t in covering_tests[:5]:
                    console.print(f"       [magenta]•[/magenta] {t}")
                if len(covering_tests) > 5:
                    console.print(
                        f"       [dim]... (+{len(covering_tests) - 5} more tests)[/dim]"
                    )
            else:
                console.print(
                    "     [dim yellow]No tests executed this line (uncovered in .coverage)[/dim yellow]"
                )

        console.print()

    if len(filtered_rows) > limit:
        console.print(
            f"  [dim]... ({len(filtered_rows) - limit} more matching mutants omitted)[/dim]\n"
        )


def clear_package_cache(package: str) -> int:
    """Selectively delete cached mutants for a specific package from SQLite cache.

    Args:
        package: Target package name.

    Returns:
        Number of deleted mutants.

    Notes/Architectural Intent:
        Removes cache records for a specific package allowing focused re-runs.
    """
    if not CACHE_FILE.exists():
        return 0

    pkg_clean = package.removeprefix("hexastack_").removeprefix("hexastack-")
    pattern = f"%hexastack_{pkg_clean}%"

    con = sqlite3.connect(CACHE_FILE)
    try:
        cur = con.cursor()
        file_rows = cur.execute(
            "SELECT id FROM SourceFile WHERE filename LIKE ?", (pattern,)
        ).fetchall()
        if not file_rows:
            return 0
        file_ids = [r[0] for r in file_rows]
        placeholders = ",".join("?" for _ in file_ids)
        mutant_rows = cur.execute(
            f"SELECT id FROM Mutant WHERE line IN (SELECT id FROM Line WHERE sourcefile IN ({placeholders}))",
            file_ids,
        ).fetchall()
        mutant_ids = [r[0] for r in mutant_rows]
        if mutant_ids:
            m_placeholders = ",".join("?" for _ in mutant_ids)
            cur.execute(
                f"DELETE FROM Mutant WHERE id IN ({m_placeholders})", mutant_ids
            )
        cur.execute(f"DELETE FROM Line WHERE sourcefile IN ({placeholders})", file_ids)
        cur.execute(f"DELETE FROM SourceFile WHERE id IN ({placeholders})", file_ids)
        con.commit()
        return len(mutant_ids)
    finally:
        con.close()


def _revert_bak_and_disk_mutations() -> None:
    """Clean up any leftover .bak files and restore modified working tree source files."""
    for bak in ROOT_DIR.glob("packages/**/*.py.bak"):
        with contextlib.suppress(OSError):
            bak.unlink(missing_ok=True)
    with contextlib.suppress(Exception):
        subprocess.run(
            ["git", "checkout", "--", "packages/"],
            cwd=ROOT_DIR,
            capture_output=True,
            check=False,
        )


def run_mutmut_on_package(pkg_dir: Path) -> int:
    """Run mutmut on a specific package directory.

    Args:
        pkg_dir: Path to the target package directory.

    Returns:
        Exit code of the mutmut subprocess.

    Raises:
        KeyboardInterrupt: If interrupted by user, after restoring working tree files.

    Notes/Architectural Intent:
        Executes mutmut mutation testing against a single package's src directory
        scoped with its corresponding unit tests directory.
    """
    src_dir = pkg_dir / "src"
    if not src_dir.is_dir():
        return 0

    rel_src = (
        src_dir.relative_to(ROOT_DIR) if src_dir.is_relative_to(ROOT_DIR) else src_dir
    )
    tests_dir = pkg_dir / "tests"
    cmd = ["mutmut", "run", "--paths-to-mutate", str(rel_src)]

    if tests_dir.is_dir():
        rel_tests = (
            tests_dir.relative_to(ROOT_DIR)
            if tests_dir.is_relative_to(ROOT_DIR)
            else tests_dir
        )
        cmd.extend(
            [
                "--runner",
                f'pytest --import-mode=importlib -n 0 -x -q --no-cov -o addopts="" {rel_tests}',
            ]
        )

    console.print(
        Panel(
            f"[bold cyan]Running mutation tests on [magenta]{pkg_dir.name}[/magenta]...[/bold cyan]",
            border_style="cyan",
        )
    )

    try:
        return subprocess.run(cmd, cwd=ROOT_DIR).returncode
    except KeyboardInterrupt:
        _revert_bak_and_disk_mutations()
        console.print(
            f"\n[yellow]⚠️ Mutation testing interrupted for {pkg_dir.name}. Restored source files.[/yellow]"
        )
        raise


def run_main() -> None:
    """CLI entrypoint for mutmut-run.

    Notes/Architectural Intent:
        Orchestrates sequential package-by-package mutation testing runs.
    """
    ensure_tool_installed("mutmut", cli_command="mutmut", extra_name="mutmut")

    parser = argparse.ArgumentParser(description="Run mutation tests.")
    parser.add_argument("-p", "--package", choices=VALID_PACKAGES)
    parser.add_argument("-a", "--all", action="store_true")
    args = parser.parse_args()

    try:
        if args.package:
            pkg_dir = get_package_directory(args.package, ROOT_DIR)
            code = run_mutmut_on_package(pkg_dir)
            sys.exit(code)
            return

        # When running across all packages (-a / default), run sequentially package-by-package
        pkg_dirs = get_package_directories(ROOT_DIR)
        exit_code = 0
        for pkg_dir in pkg_dirs:
            code = run_mutmut_on_package(pkg_dir)
            if code != 0 and exit_code == 0:
                exit_code = code

        sys.exit(exit_code)
    except KeyboardInterrupt:
        _revert_bak_and_disk_mutations()
        console.print(
            "[bold red]\n🛑 Mutation testing aborted by user. Working tree clean.[/bold red]"
        )
        sys.exit(130)


def inspect_main() -> None:
    """CLI entrypoint for mutmut-inspect.

    Notes/Architectural Intent:
        Parses inspection arguments and queries .mutmut-cache to display classified triage tables.
    """
    ensure_tool_installed("mutmut", cli_command="mutmut", extra_name="mutmut")

    parser = argparse.ArgumentParser(
        description="Inspect .mutmut-cache with automated mutant classification (Critical vs Ignorable)"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Display package-level and triage classification summary.",
    )
    parser.add_argument(
        "-p",
        "--package",
        default=None,
        help="Filter surviving mutants by package name (e.g. db, auth, events, grpc).",
    )
    parser.add_argument(
        "-f",
        "--file",
        default=None,
        help="Filter surviving mutants by filename pattern (e.g. exception.py).",
    )
    parser.add_argument(
        "-a",
        "--actionable-only",
        action="store_true",
        help="Only display actionable critical mutants (skip ignorable / equivalent).",
    )
    parser.add_argument(
        "-c",
        "--correlate-coverage",
        action="store_true",
        help="Cross-reference .coverage database to identify test functions executing mutant lines.",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=25,
        help="Maximum number of mutant lines to display (default: 25).",
    )

    args = parser.parse_args()

    con = get_db_connection()
    if not con:
        sys.exit(1)

    try:
        if args.summary or (not args.package and not args.file):
            show_summary(con)

        if args.package:
            show_file_mutants(
                con,
                f"hexastack_{args.package}",
                limit=args.limit,
                actionable_only=args.actionable_only,
                correlate_coverage=args.correlate_coverage,
            )

        if args.file:
            show_file_mutants(
                con,
                args.file,
                limit=args.limit,
                actionable_only=args.actionable_only,
                correlate_coverage=args.correlate_coverage,
            )
    finally:
        con.close()


__all__ = [
    "classify_mutant_line",
    "clear_package_cache",
    "get_db_connection",
    "inspect_main",
    "MutantCategory",
    "run_main",
    "run_mutmut_on_package",
    "show_file_mutants",
    "show_summary",
]
