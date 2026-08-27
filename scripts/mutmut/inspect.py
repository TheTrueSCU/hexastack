"""Mutmut cache inspection script for Hexastack.

Usage:
    # Summary of survivors by package
    uv run python scripts/inspect_mutants.py --summary

    # List surviving mutants in a specific package or file pattern
    uv run python scripts/inspect_mutants.py --package db
    uv run python scripts/inspect_mutants.py --file engine.py
    uv run python scripts/inspect_mutants.py --file bootstrap.py --limit 20
"""

import argparse
import enum
import re
import sqlite3
import sys

from scripts._common import get_repo_root

ROOT_DIR = get_repo_root()
CACHE_FILE = ROOT_DIR / ".mutmut-cache"


class MutantCategory(enum.StrEnum):
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
    """Connect to SQLite mutmut cache if it exists."""
    if not CACHE_FILE.exists():
        print(f"Error: Cache file not found at {CACHE_FILE}")
        return None
    return sqlite3.connect(CACHE_FILE)


def show_summary(con: sqlite3.Connection) -> None:
    """Print high-level summary of surviving mutants by package with triage classification."""
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
        print("No surviving mutants found in cache!")
        return

    package_stats: dict[str, dict[str, int]] = {}
    for _, filename, line_str in rows:
        match = re.search(r"hexastack_([a-z0-9_]+)", filename)
        pkg = match.group(1) if match else "other"
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

    print(
        "\n================================================================================"
    )
    print(" Surviving Mutants Triage Summary by Package")
    print(
        "================================================================================"
    )
    print(
        f"  {'Package':<18} | {'Total':<6} | {'🔴 Critical':<12} | {'🟡 Equivalent':<14} | {'🟢 Ignorable':<12}"
    )
    print("  " + "-" * 74)

    for pkg, stats in sorted(
        package_stats.items(), key=lambda x: x[1]["critical"], reverse=True
    ):
        print(
            f"  hexastack_{pkg:<8} | {stats['total']:<6d} | "
            f"{stats['critical']:<12d} | {stats['equivalent']:<14d} | {stats['ignorable']:<12d}"
        )
    print()


def show_file_mutants(
    con: sqlite3.Connection,
    pattern: str,
    limit: int = 25,
    actionable_only: bool = False,
) -> None:
    """Print classified line details for surviving mutants matching a pattern."""
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
        print(f"No surviving mutants matching '{pattern}'.")
        return

    filtered_rows = []
    for row in rows:
        cat, reason = classify_mutant_line(row[3].strip(), row[1])
        if actionable_only and cat != MutantCategory.CRITICAL:
            continue
        filtered_rows.append((row, cat, reason))

    title_suffix = " (Actionable Critical Only)" if actionable_only else ""
    print(
        f"\n=== Surviving Mutants matching '{pattern}' ({len(filtered_rows)} total){title_suffix} ==="
    )

    for row, cat, reason in filtered_rows[:limit]:
        rel_path = row[1].replace(str(ROOT_DIR) + "/", "")
        line_str = row[3].strip()
        icon = (
            "🔴"
            if cat == MutantCategory.CRITICAL
            else ("🟡" if cat == MutantCategory.EQUIVALENT else "🟢")
        )
        print(f"  {icon} Mutant {row[0]:<4} [{cat.value:<10}] | {rel_path}:{row[2]}")
        print(f"     Code:   {line_str}")
        print(f"     Reason: {reason}\n")

    if len(filtered_rows) > limit:
        print(f"  ... ({len(filtered_rows) - limit} more matching mutants omitted)\n")


def main() -> None:
    """Parse CLI arguments and dispatch cache inspection."""
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

    if args.summary or (not args.package and not args.file):
        show_summary(con)

    if args.package:
        show_file_mutants(
            con,
            f"hexastack_{args.package}",
            limit=args.limit,
            actionable_only=args.actionable_only,
        )

    if args.file:
        show_file_mutants(
            con,
            args.file,
            limit=args.limit,
            actionable_only=args.actionable_only,
        )


if __name__ == "__main__":
    main()
