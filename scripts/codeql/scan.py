"""Local CodeQL Security and Quality Scanner with Installation Guards.

Notes/Architectural Intent:
    Provides a standardized local CodeQL scan command (`uv run codeql-scan`)
    that creates a temporary CodeQL database for Python packages, runs security
    and quality query suites, and outputs human-readable findings as well as
    standard SARIF reports. Gracefully skips execution with an informative
    notice if `shutil.which("codeql")` indicates the binary is not installed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts._common import get_repo_root

__all__ = [
    "main",
    "run_local_codeql_scan",
]

console = Console()


def run_local_codeql_scan(
    query_suite: str = "codeql/python-queries",
    output_sarif: Path | None = None,
    threads: int = 0,
) -> int:
    """Execute local CodeQL database creation and analysis.

    Args:
        query_suite: CodeQL query pack or suite to evaluate (default: 'codeql/python-queries').
        output_sarif: Optional output path for the SARIF report file.
        threads: Number of worker threads (0 = auto-detect).

    Returns:
        0 on clean scan / no critical findings, 1 on scan errors or alerts.
    """
    codeql_bin = shutil.which("codeql")
    if not codeql_bin:
        console.print(
            Panel(
                "[yellow]⚠️  CodeQL CLI ('codeql') not found in system PATH.\n"
                "To enable local CodeQL analysis, install CodeQL via mise or your package manager:\n\n"
                "  mise use -g github:github/codeql-cli-binaries\n\n"
                "Skipping local CodeQL scan.[/yellow]",
                title="[bold yellow]CodeQL Scanner Notice[/bold yellow]",
                border_style="yellow",
            )
        )
        return 0

    root = get_repo_root()

    with tempfile.TemporaryDirectory(prefix="hexastack-codeql-db-") as tmp_db_dir:
        db_path = Path(tmp_db_dir) / "db"
        sarif_file = output_sarif or (Path(tmp_db_dir) / "results.sarif")

        console.print(
            f"[bold cyan]🔍 1. Creating CodeQL database at {db_path}...[/bold cyan]"
        )
        create_cmd = [
            codeql_bin,
            "database",
            "create",
            str(db_path),
            "--language=python",
            f"--source-root={root}",
            "--overwrite",
        ]
        if threads > 0:
            create_cmd.append(f"--threads={threads}")

        res = subprocess.run(create_cmd, cwd=root, capture_output=True, text=True)
        if res.returncode != 0:
            console.print(
                Panel(
                    f"[bold red]CodeQL database creation failed:\n{res.stderr}[/bold red]",
                    title="[bold red]Database Creation Error[/bold red]",
                )
            )
            return 1

        console.print(
            f"[bold cyan]⚡ 2. Analyzing database with query pack '{query_suite}'...[/bold cyan]"
        )
        analyze_cmd = [
            codeql_bin,
            "database",
            "analyze",
            str(db_path),
            query_suite,
            "--format=sarif-latest",
            f"--output={sarif_file}",
        ]
        if threads > 0:
            analyze_cmd.append(f"--threads={threads}")

        res = subprocess.run(analyze_cmd, cwd=root, capture_output=True, text=True)
        if res.returncode != 0:
            console.print(
                Panel(
                    f"[bold red]CodeQL analysis failed:\n{res.stderr}[/bold red]",
                    title="[bold red]Analysis Error[/bold red]",
                )
            )
            return 1

        # Parse and display SARIF results
        return _display_sarif_results(sarif_file, root)


def _display_sarif_results(sarif_path: Path, root: Path) -> int:
    """Parse and print SARIF results in a structured terminal table."""
    import json

    if not sarif_path.is_file():
        console.print("[bold red]SARIF results file not generated.[/bold red]")
        return 1

    try:
        data = json.loads(sarif_path.read_text(encoding="utf-8"))
    except Exception as exc:
        console.print(f"[bold red]Failed to parse SARIF output:[/bold red] {exc}")
        return 1

    runs: list[dict[str, Any]] = data.get("runs", [])
    results: list[dict[str, Any]] = []
    for run in runs:
        results.extend(run.get("results", []))

    if not results:
        console.print(
            Panel(
                "[bold green]🎉 Clean! Local CodeQL scan found 0 security or quality alerts.[/bold green]",
                title="[bold green]CodeQL Scan Results[/bold green]",
                border_style="green",
            )
        )
        return 0

    table = Table(
        title=f"[bold cyan]Local CodeQL Scan Findings (Total: {len(results)})[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Rule ID", style="bold")
    table.add_column("Level", width=10)
    table.add_column("Location", style="blue")
    table.add_column("Message")

    for r in results:
        rule_id = r.get("ruleId", "unknown")
        level = r.get("level", "warning")
        msg = r.get("message", {}).get("text", "")

        locations = r.get("locations", [])
        loc_str = "unknown"
        if locations:
            phys = locations[0].get("physicalLocation", {})
            uri = phys.get("artifactLocation", {}).get("uri", "")
            line = phys.get("region", {}).get("startLine", "-")
            loc_str = f"{uri}:{line}"

        if level in ("error", "critical"):
            level_styled = f"[bold red]{level}[/bold red]"
        elif level == "warning":
            level_styled = f"[bold yellow]{level}[/bold yellow]"
        else:
            level_styled = f"[dim cyan]{level}[/dim cyan]"

        table.add_row(rule_id, level_styled, loc_str, msg)

    console.print(table)
    return 1 if any(r.get("level") in ("error", "critical") for r in results) else 0


def main() -> int:
    """CLI entrypoint for codeql-scan."""
    parser = argparse.ArgumentParser(
        description="Run local CodeQL security and quality analysis with auto-detection."
    )
    parser.add_argument(
        "--suite",
        "-s",
        type=str,
        default="codeql/python-queries",
        help="CodeQL query suite or pack (default: 'codeql/python-queries').",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Optional destination path for generated SARIF report.",
    )
    parser.add_argument(
        "--threads",
        "-t",
        type=int,
        default=0,
        help="Number of analysis threads (0 for auto).",
    )
    args = parser.parse_args()

    return run_local_codeql_scan(
        query_suite=args.suite,
        output_sarif=args.output,
        threads=args.threads,
    )


if __name__ == "__main__":
    sys.exit(main())
