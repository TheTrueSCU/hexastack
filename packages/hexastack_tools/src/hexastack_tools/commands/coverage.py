"""Coverage inspection, test impact analysis, and architectural boundary verification."""

from __future__ import annotations

import argparse
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from coverage import CoverageData
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.utils.workspace import (
    ensure_tool_installed,
    get_repo_root,
)

console = Console()
ROOT_DIR = get_repo_root()
COV_DB = ROOT_DIR / ".coverage"
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def get_changed_lines(
    git_ref: str | None = None,
    root_dir: Path | None = None,
) -> dict[Path, set[int]]:
    """Extract added and modified 1-based line numbers per file using git diff.

    Args:
        git_ref: Git ref or revision to diff against (e.g., 'main', 'HEAD~1').
        root_dir: Root directory for relative path resolution.

    Returns:
        Mapping of absolute Path to set of modified 1-based line numbers.

    Notes/Architectural Intent:
        Parses git diff hunks to correlate modified source lines with coverage executions.
    """
    root = root_dir or ROOT_DIR
    cmd = ["git", "diff", "-U0"]
    if git_ref:
        cmd.append(git_ref)

    result = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    changed: dict[Path, set[int]] = defaultdict(set)
    current_file: Path | None = None

    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            rel_path = line.removeprefix("+++ b/")
            current_file = (root / rel_path).resolve()
        elif line.startswith("@@") and current_file is not None:
            match = HUNK_RE.match(line)
            if not match:
                continue

            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1

            if count > 0:
                lines = range(start, start + count)
                changed[current_file].update(lines)

    return changed


def find_impacted_tests(
    changed_lines: dict[Path, set[int]],
    cov_path: Path | None = None,
) -> set[str]:
    """Correlate changed line numbers against .coverage dynamic contexts.

    Args:
        changed_lines: Mapping of file Path to changed line numbers.
        cov_path: Path to the .coverage database.

    Returns:
        Set of pytest test node IDs that execute the changed lines.

    Notes/Architectural Intent:
        Performs Test Impact Analysis (TIA) by mapping line numbers to test contexts.
    """
    db_file = cov_path or COV_DB
    if not db_file.is_file():
        return set()

    cov_data = CoverageData(str(db_file))
    cov_data.read()

    measured_files = {Path(p).resolve(): p for p in cov_data.measured_files()}
    impacted_tests: set[str] = set()

    for file_path, lines in changed_lines.items():
        cov_key = measured_files.get(file_path.resolve())
        if not cov_key:
            continue

        contexts_by_line = cov_data.contexts_by_lineno(cov_key)
        for lineno in lines:
            for test_context in contexts_by_line.get(lineno, []):
                if test_context:
                    impacted_tests.add(test_context)

    return impacted_tests


def get_tests_covering_line(
    file_path: str | Path,
    line_number: int,
    cov_path: Path | None = None,
) -> list[str]:
    """Retrieve all non-empty test function contexts that executed a specific file line.

    Args:
        file_path: Path to the source file.
        line_number: 1-based line number.
        cov_path: Optional path to .coverage database.

    Returns:
        List of test function context strings.

    Notes/Architectural Intent:
        Used by mutant-coverage correlation to identify which tests covered a surviving mutant.
    """
    db_file = cov_path or COV_DB
    if not db_file.is_file():
        return []

    cov_data = CoverageData(str(db_file))
    cov_data.read()

    target_resolved = Path(file_path).resolve()
    for measured in cov_data.measured_files():
        if Path(measured).resolve() == target_resolved:
            contexts = cov_data.contexts_by_lineno(measured).get(line_number, [])
            return sorted([c for c in contexts if c])

    return []


def audit_layer_boundary_leaks(cov_path: Path | None = None) -> list[tuple[str, str]]:
    """Identify domain unit tests that execute infrastructure or adapter files.

    Args:
        cov_path: Optional path to .coverage database.

    Returns:
        List of (test_context, leaked_file_path) tuples.

    Notes/Architectural Intent:
        Enforces clean architectural isolation by verifying domain unit tests never
        touch database, network, or external adapter implementations.
    """
    db_file = cov_path or COV_DB
    if not db_file.is_file():
        return []

    con = sqlite3.connect(db_file)
    try:
        cur = con.cursor()
        query = """
        SELECT DISTINCT
            c.context,
            f.path
        FROM line_bits lb
        JOIN file f ON lb.file_id = f.id
        JOIN context c ON lb.context_id = c.id
        WHERE c.context LIKE '%test_domain%'
          AND (f.path LIKE '%/infra/%' OR f.path LIKE '%/adapters/%' OR f.path LIKE '%/infrastructure/%')
        ORDER BY c.context
        """
        return cur.execute(query).fetchall()
    except Exception:
        return []
    finally:
        con.close()


def audit_redundant_tests(cov_path: Path | None = None) -> list[str]:
    """Find tests that cover zero branches uniquely across the entire test suite.

    Args:
        cov_path: Optional path to .coverage database.

    Returns:
        List of redundant test context strings.

    Notes/Architectural Intent:
        Identifies tests whose entire branch execution footprint is already covered
        by other tests in the suite.
    """
    db_file = cov_path or COV_DB
    if not db_file.is_file():
        return []

    con = sqlite3.connect(db_file)
    try:
        cur = con.cursor()
        query = """
        WITH ArcCoverage AS (
            SELECT file_id, from_line, to_line, context_id
            FROM arc
            WHERE context_id != (SELECT id FROM context WHERE context = '')
        ),
        UniqueCoverage AS (
            SELECT file_id, from_line, to_line
            FROM ArcCoverage
            GROUP BY file_id, from_line, to_line
            HAVING COUNT(DISTINCT context_id) = 1
        )
        SELECT DISTINCT
            c.context
        FROM context c
        WHERE c.id NOT IN (
            SELECT DISTINCT ac.context_id
            FROM ArcCoverage ac
            JOIN UniqueCoverage uc
              ON ac.file_id = uc.file_id
             AND ac.from_line = uc.from_line
             AND ac.to_line = uc.to_line
        )
        AND c.context != ''
        ORDER BY c.context
        """
        rows = cur.execute(query).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []
    finally:
        con.close()


def impact_main() -> None:
    """CLI entrypoint for pytest-impact.

    Notes/Architectural Intent:
        Executes only the test subset impacted by git changes.
    """
    ensure_tool_installed("pytest", cli_command="pytest")

    parser = argparse.ArgumentParser(
        description="Run only tests impacted by modified lines using git diff and .coverage data."
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Git ref or branch to diff against (e.g. 'main', 'origin/main', 'HEAD~1'). Defaults to unstaged/staged working tree.",
    )
    parser.add_argument(
        "--cov-file",
        default=str(COV_DB),
        help="Path to .coverage database (default: .coverage)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected test targets without executing pytest.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Extra flags passed directly to pytest (e.g. -- -v -s)",
    )
    args = parser.parse_args()

    cov_file = Path(args.cov_file)
    if not cov_file.is_file():
        console.print(
            Panel.fit(
                f"[bold red]Coverage database '{cov_file}' not found.[/bold red]\n"
                f"[yellow]Run full pytest with coverage first: [cyan]uv run pytest[/cyan][/yellow]",
                border_style="red",
            )
        )
        sys.exit(1)

    changed_lines = get_changed_lines(args.base)
    if not changed_lines:
        console.print("[green]✨ No source line modifications detected.[/green]")
        sys.exit(0)

    impacted_tests = find_impacted_tests(changed_lines, cov_file)
    if not impacted_tests:
        console.print(
            "[yellow]ℹ️ Modified lines have no corresponding tests in coverage data.[/yellow]"
        )
        sys.exit(0)

    console.print(
        Panel.fit(
            f"[bold cyan]Discovered {len(impacted_tests)} impacted test(s):[/bold cyan]",
            border_style="cyan",
        )
    )
    for test in sorted(impacted_tests):
        console.print(f"  [green]*[/green] {test}")

    if args.dry_run:
        return

    extra_args = (
        args.pytest_args[1:]
        if args.pytest_args and args.pytest_args[0] == "--"
        else args.pytest_args
    )

    cmd = ["pytest"] + sorted(impacted_tests) + (extra_args or [])
    console.print(f"\n[dim]Executing: {' '.join(cmd)}[/dim]\n")
    sys.exit(subprocess.run(cmd, cwd=ROOT_DIR).returncode)


def boundary_audit_main() -> None:
    """CLI entrypoint for pytest-boundary-audit.

    Notes/Architectural Intent:
        Audits .coverage execution contexts to verify domain unit tests never execute infra/adapters.
    """
    parser = argparse.ArgumentParser(
        description="Audit .coverage execution contexts for hexagonal architectural layer leaks."
    )
    parser.add_argument(
        "--cov-file",
        default=str(COV_DB),
        help="Path to .coverage database (default: .coverage)",
    )
    args = parser.parse_args()

    cov_file = Path(args.cov_file)
    if not cov_file.is_file():
        console.print(
            Panel.fit(
                f"[bold red]Coverage database '{cov_file}' not found.[/bold red]\n"
                f"[yellow]Run pytest with coverage first: [cyan]uv run pytest[/cyan][/yellow]",
                border_style="red",
            )
        )
        sys.exit(1)

    leaks = audit_layer_boundary_leaks(cov_file)
    if not leaks:
        console.print(
            Panel.fit(
                "[bold green]✨ Zero architectural layer leaks detected in test execution contexts![/bold green]",
                border_style="green",
            )
        )
        return

    table = Table(
        title="[bold red]Architectural Test Boundary Leaks[/bold red]",
        border_style="red",
    )
    table.add_column("Violating Domain Test Context", style="bold magenta")
    table.add_column("Leaked Dependency File", style="cyan")

    for test_ctx, leaked_file in leaks:
        rel_file = (
            Path(leaked_file).relative_to(ROOT_DIR)
            if Path(leaked_file).is_relative_to(ROOT_DIR)
            else leaked_file
        )
        table.add_row(test_ctx, str(rel_file))

    console.print(table)
    sys.exit(1)


def redundancy_audit_main() -> None:
    """CLI entrypoint for pytest-redundancy-audit.

    Notes/Architectural Intent:
        Identifies tests providing zero unique branch coverage across the suite.
    """
    parser = argparse.ArgumentParser(
        description="Identify redundant unit tests providing zero unique branch coverage."
    )
    parser.add_argument(
        "--cov-file",
        default=str(COV_DB),
        help="Path to .coverage database (default: .coverage)",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=25,
        help="Maximum redundant tests to display (default: 25)",
    )
    args = parser.parse_args()

    cov_file = Path(args.cov_file)
    if not cov_file.is_file():
        console.print(
            Panel.fit(
                f"[bold red]Coverage database '{cov_file}' not found.[/bold red]\n"
                f"[yellow]Run pytest with branch coverage first: [cyan]uv run pytest[/cyan][/yellow]",
                border_style="red",
            )
        )
        sys.exit(1)

    redundant = audit_redundant_tests(cov_file)
    if not redundant:
        console.print(
            Panel.fit(
                "[bold green]✨ All tests contribute unique branch coverage (zero full redundancy).[/bold green]",
                border_style="green",
            )
        )
        return

    table = Table(
        title=f"[bold yellow]Redundant Test Candidates ({len(redundant)} total)[/bold yellow]",
        border_style="yellow",
    )
    table.add_column("Test Context", style="bold white")

    for test_ctx in redundant[: args.limit]:
        table.add_row(test_ctx)

    console.print(table)
    if len(redundant) > args.limit:
        console.print(
            f"[dim]... ({len(redundant) - args.limit} more redundant tests omitted)[/dim]\n"
        )


__all__ = [
    "audit_layer_boundary_leaks",
    "audit_redundant_tests",
    "boundary_audit_main",
    "find_impacted_tests",
    "get_changed_lines",
    "get_tests_covering_line",
    "impact_main",
    "redundancy_audit_main",
]
