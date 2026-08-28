"""Mutmut mutation testing runner and cache inspection commands."""

from __future__ import annotations

import argparse
import enum
import sqlite3
import subprocess
import sys

from hexastack_tools.utils.workspace import VALID_PACKAGES, get_repo_root

ROOT_DIR = get_repo_root()
CACHE_FILE = ROOT_DIR / ".mutmut-cache"


class MutantCategory(enum.StrEnum):
    CRITICAL = "CRITICAL"
    EQUIVALENT = "EQUIVALENT"
    IGNORABLE = "IGNORABLE"


def clear_package_cache(package: str) -> int:
    """Selectively delete cached mutants for a specific package from SQLite cache."""
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
            f"SELECT id FROM Mutant WHERE line_id IN (SELECT id FROM Line WHERE source_file_id IN ({placeholders}))",
            file_ids,
        ).fetchall()
        mutant_ids = [r[0] for r in mutant_rows]
        if mutant_ids:
            m_placeholders = ",".join("?" for _ in mutant_ids)
            cur.execute(
                f"DELETE FROM Mutation WHERE mutant_id IN ({m_placeholders})",
                mutant_ids,
            )
            cur.execute(
                f"DELETE FROM Mutant WHERE id IN ({m_placeholders})", mutant_ids
            )
        cur.execute(
            f"DELETE FROM Line WHERE source_file_id IN ({placeholders})", file_ids
        )
        cur.execute(f"DELETE FROM SourceFile WHERE id IN ({placeholders})", file_ids)
        con.commit()
        return len(mutant_ids)
    finally:
        con.close()


def run_main() -> None:
    """CLI entrypoint for mutmut-run."""
    parser = argparse.ArgumentParser(description="Run mutation tests.")
    parser.add_argument("-p", "--package", choices=VALID_PACKAGES)
    parser.add_argument("-a", "--all", action="store_true")
    args = parser.parse_args()

    cmd = ["mutmut", "run"]
    if args.package:
        cmd.extend(["--paths-to-mutate", f"packages/hexastack_{args.package}/src"])
    sys.exit(subprocess.run(cmd, cwd=ROOT_DIR).returncode)


def inspect_main() -> None:
    """CLI entrypoint for mutmut-inspect."""
    cmd = ["mutmut", "results"]
    sys.exit(subprocess.run(cmd, cwd=ROOT_DIR).returncode)


__all__ = [
    "MutantCategory",
    "clear_package_cache",
    "inspect_main",
    "run_main",
]
