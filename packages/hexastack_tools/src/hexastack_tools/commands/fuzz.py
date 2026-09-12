"""Coverage-guided and adversarial security fuzz runner.

Notes/Architectural Intent:
    Orchestrates Atheris coverage-guided fuzz harnesses and OWASP security fuzzing suites,
    evaluating algorithmic ReDoS immunity in hexastack-logging, Protobuf compiler parser safety
    in hexastack-grpc, and API injection resistance in hexastack-fastapi.
"""

from __future__ import annotations

import argparse
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.infra.handlers.analysis import run_target_fuzz

console = Console()


def display_fuzz_results(results: list[dict[str, Any]]) -> int:
    """Render fuzzing results in a styled Rich table.

    Args:
        results: List of execution result dictionaries.

    Returns:
        0 if all targets passed, 1 if any target failed.
    """
    table = Table(
        title="[bold cyan]Hexastack Security Fuzzing Audit[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Target", style="cyan")
    table.add_column("Engine", style="yellow")
    table.add_column("Runs", justify="right", style="blue")
    table.add_column("Duration (s)", justify="right", style="white")
    table.add_column("Crashes", justify="right")
    table.add_column("ReDoS / Invariants", justify="right")
    table.add_column("Status", justify="center")

    all_passed = True

    for r in results:
        crashes = r.get("crashes", 0)
        violations = r.get("redos_violations", 0)
        passed = r.get("passed", False) and crashes == 0 and violations == 0
        if not passed:
            all_passed = False

        crash_style = "bold green" if crashes == 0 else "bold red"
        viol_style = "bold green" if violations == 0 else "bold red"
        status_badge = (
            "[bold green]PASS[/bold green]" if passed else "[bold red]FAIL[/bold red]"
        )

        table.add_row(
            r.get("target", "unknown"),
            r.get("engine", "unknown"),
            str(r.get("runs", 0)),
            f"{r.get('duration_seconds', 0.0):.3f}",
            f"[{crash_style}]{crashes}[/{crash_style}]",
            f"[{viol_style}]{violations}[/{viol_style}]",
            status_badge,
        )

    console.print(table)

    if all_passed:
        console.print(
            Panel(
                "[bold green]✨ All fuzzing targets passed with zero crashes, zero ReDoS, and zero invariant violations.[/bold green]",
                border_style="green",
            )
        )
        return 0

    console.print(
        Panel(
            "[bold red]❌ One or more fuzzing harnesses detected crashes or invariant violations.[/bold red]",
            border_style="red",
        )
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for fuzz-run command.

    Args:
        argv: Optional command-line arguments list.

    Returns:
        Exit code (0 if all harnesses passed, 1 otherwise).

    Notes/Architectural Intent:
        Dispatches FuzzRunCommand across the governance bus and renders
        results via the configured AnalysisPresenterPort.
    """
    parser = argparse.ArgumentParser(
        description="Run Atheris coverage-guided and OWASP security fuzz harnesses across Hexastack packages."
    )
    parser.add_argument(
        "-t",
        "--target",
        default="all",
        choices=["all", "sanitizer", "proto", "owasp"],
        help="Target fuzz harness to execute (default: all)",
    )
    parser.add_argument(
        "-n",
        "--runs",
        type=int,
        default=1000,
        help="Number of fuzzed runs per harness (default: 1000)",
    )
    parser.add_argument(
        "-e",
        "--engine",
        default="auto",
        choices=["auto", "atheris", "standalone"],
        help="Fuzzing engine (default: auto)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json", "markdown"],
        default="table",
        help="Output presentation format (default: table).",
    )

    args = parser.parse_args(argv)

    from hexastack_tools.adapters.presenters.analysis import (
        create_analysis_presenter,
    )
    from hexastack_tools.domain.analysis import FuzzRunCommand
    from hexastack_tools.infra.bootstrap import create_governance_bus

    bus = create_governance_bus()
    presenter = create_analysis_presenter(args.format)

    cmd = FuzzRunCommand(
        target=args.target,
        runs=args.runs,
        engine=args.engine,
    )
    try:
        report = bus.dispatch(cmd)
        return presenter.present_fuzz(report)
    except Exception as exc:
        console.print(f"[bold red]Fuzz runner error:[/bold red] {exc}")
        return 1


__all__ = [
    "display_fuzz_results",
    "main",
    "run_target_fuzz",
]
