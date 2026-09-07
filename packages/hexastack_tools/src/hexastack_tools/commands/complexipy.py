"""Filtered complexipy runner displaying only failing/exceeding methods."""

from __future__ import annotations

import argparse
import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_complexipy(
    paths: list[str],
    max_complexity: int = 25,
) -> int:
    """Run complexipy with --plain output and render only functions exceeding the threshold.

    Args:
        paths: List of directory or file paths to audit.
        max_complexity: Maximum allowed cognitive complexity per function.

    Returns:
        0 if all functions pass within allowed complexity, 1 otherwise.

    Notes/Architectural Intent:
        Standard complexipy emits verbose PASS lines for every single function across all
        subpackages (several thousand lines). This runner parses the machine-readable output,
        filtering out passing entries and highlighting only failing hotspots.
    """
    cmd = [
        "complexipy",
        *paths,
        "--max-complexity-allowed",
        str(max_complexity),
        "--plain",
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 and not proc.stdout.strip():
        if proc.stderr:
            console.print(
                f"[bold red]complexipy error:[/bold red] {proc.stderr.strip()}"
            )
        return proc.returncode

    raw_output = proc.stdout.strip()

    violations: list[tuple[str, str, int]] = []

    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 3:
            file_path = parts[0]
            func_name = parts[1]
            try:
                score = int(parts[2])
                if score > max_complexity:
                    violations.append((file_path, func_name, score))
            except ValueError:
                continue

    if violations:
        table = Table(
            title=f"[bold red]Cognitive Complexity Violations (> {max_complexity})[/bold red]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("File", style="cyan")
        table.add_column("Function / Method", style="bold yellow")
        table.add_column("Complexity Score", justify="right", style="bold red")

        for file_path, func_name, score in sorted(
            violations, key=lambda x: x[2], reverse=True
        ):
            table.add_row(file_path, func_name, str(score))

        console.print(table)
        console.print(
            Panel(
                f"[bold red]❌ {len(violations)} function(s) exceeded the maximum allowed cognitive complexity ({max_complexity}).[/bold red]\n"
                "Refactor these methods by extracting subroutines or helper functions.",
                border_style="red",
            )
        )
        return 1

    console.print(
        Panel(
            f"[bold green]✨ All functions across {len(paths)} target(s) are within allowed cognitive complexity (≤ {max_complexity}).[/bold green]",
            border_style="green",
        )
    )
    return 0


def main() -> int:
    """CLI entrypoint for complexipy runner."""
    parser = argparse.ArgumentParser(
        description="Run complexipy filtering output to failing methods only."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["packages"],
        help="Target directories or files (default: packages)",
    )
    parser.add_argument(
        "--max-complexity-allowed",
        type=int,
        default=25,
        help="Maximum allowed cognitive complexity score (default: 25)",
    )
    args = parser.parse_args()
    return run_complexipy(args.paths, max_complexity=args.max_complexity_allowed)


__all__ = [
    "main",
    "run_complexipy",
]
