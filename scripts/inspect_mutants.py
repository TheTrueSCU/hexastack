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
import re
import sqlite3
import sys

from _common import get_repo_root

ROOT_DIR = get_repo_root()
CACHE_FILE = ROOT_DIR / ".mutmut-cache"


def get_db_connection() -> sqlite3.Connection | None:
    """Connect to SQLite mutmut cache if it exists."""
    if not CACHE_FILE.exists():
        print(f"Error: Cache file not found at {CACHE_FILE}")
        return None
    return sqlite3.connect(CACHE_FILE)


def show_summary(con: sqlite3.Connection) -> None:
    """Print high-level summary of surviving mutants by package."""
    cur = con.cursor()
    query = """
    SELECT sf.filename, count(m.id) as survivor_count
    FROM Mutant m
    JOIN Line l ON m.line = l.id
    JOIN SourceFile sf ON l.sourcefile = sf.id
    WHERE m.status IN ('bad_survived', 'bad_timeout')
    GROUP BY sf.filename
    ORDER BY survivor_count DESC
    """
    rows = cur.execute(query).fetchall()
    if not rows:
        print("No surviving mutants found in cache!")
        return

    package_counts: dict[str, int] = {}
    for filename, count in rows:
        match = re.search(r"hexastack_([a-z0-9_]+)", filename)
        pkg = match.group(1) if match else "other"
        package_counts[pkg] = package_counts.get(pkg, 0) + count

    print("\n========================================================")
    print(" Surviving Mutants Summary by Package")
    print("========================================================")
    for pkg, count in sorted(package_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  hexastack_{pkg:<14}: {count:4d} survivors")

    print("\n--- Top Files with Survivors ---")
    for filename, count in rows[:20]:
        rel_path = filename.replace(str(ROOT_DIR) + "/", "")
        print(f"  {count:4d}  {rel_path}")
    print()


def show_file_mutants(
    con: sqlite3.Connection,
    pattern: str,
    limit: int = 15,
) -> None:
    """Print line details for surviving mutants matching a pattern."""
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

    print(f"\n=== Surviving Mutants matching '{pattern}' ({len(rows)} total) ===")
    for row in rows[:limit]:
        rel_path = row[1].replace(str(ROOT_DIR) + "/", "")
        line_str = row[3].strip()
        print(f"  Mutant {row[0]:<4} | {rel_path}:{row[2]} -> {line_str}")
    if len(rows) > limit:
        print(f"  ... ({len(rows) - limit} more matching mutants omitted)")
    print()


def main() -> None:
    """Parse CLI arguments and dispatch cache inspection."""
    parser = argparse.ArgumentParser(
        description="Inspect .mutmut-cache for surviving mutants"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Display package-level and top-file survivor summaries.",
    )
    parser.add_argument(
        "-p",
        "--package",
        default=None,
        help="Filter surviving mutants by package name (e.g. db, auth, events).",
    )
    parser.add_argument(
        "-f",
        "--file",
        default=None,
        help="Filter surviving mutants by filename pattern (e.g. engine.py).",
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
        show_file_mutants(con, f"hexastack_{args.package}", limit=args.limit)

    if args.file:
        show_file_mutants(con, args.file, limit=args.limit)


if __name__ == "__main__":
    main()
