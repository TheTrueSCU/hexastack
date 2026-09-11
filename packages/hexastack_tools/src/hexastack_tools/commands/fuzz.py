"""Coverage-guided and adversarial security fuzz runner.

Notes/Architectural Intent:
    Orchestrates Atheris coverage-guided fuzz harnesses and OWASP security fuzzing suites,
    evaluating algorithmic ReDoS immunity in hexastack-logging, Protobuf compiler parser safety
    in hexastack-grpc, and API injection resistance in hexastack-fastapi.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import subprocess
import sys
import time
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hexastack_tools.utils.workspace import get_repo_root

console = Console()


def run_target_fuzz(
    target: str,
    runs: int = 1000,
    engine: str = "auto",
) -> list[dict[str, Any]]:
    """Execute selected fuzzing targets.

    Args:
        target: Target name ('all', 'sanitizer', 'proto', 'owasp').
        runs: Number of fuzzing iterations to run per target.
        engine: Engine selection ('auto', 'atheris', 'standalone').

    Returns:
        List of dictionaries with run summary metrics.

    Raises:
        ValueError: If target name is unrecognized.
    """
    repo_root = get_repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    results: list[dict[str, Any]] = []

    use_atheris = False
    if engine in ("auto", "atheris"):
        try:
            use_atheris = importlib.util.find_spec("atheris") is not None
        except Exception:
            use_atheris = False

    if target in ("all", "sanitizer"):
        mod_san = importlib.import_module("fuzz.fuzz_log_sanitizer")
        runner = (
            mod_san.run_atheris
            if use_atheris and engine != "standalone"
            else mod_san.run_standalone
        )
        results.append(runner(runs=runs))

    if target in ("all", "proto"):
        mod_proto = importlib.import_module("fuzz.fuzz_proto_compiler")
        # Proto compiler runs are heavier; scale default if high
        proto_runs = min(runs, 500) if runs > 500 else runs
        runner = (
            mod_proto.run_atheris
            if use_atheris and engine != "standalone"
            else mod_proto.run_standalone
        )
        results.append(runner(runs=proto_runs))

    if target in ("all", "owasp"):
        start_time = time.perf_counter()
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "packages/hexastack_fastapi/tests/properties/test_owasp_security_fuzz.py",
            "-q",
            "--no-cov",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        dur = round(time.perf_counter() - start_time, 3)
        passed = proc.returncode == 0
        results.append(
            {
                "target": "OWASP Security Fuzz",
                "engine": "hypothesis",
                "runs": runs,
                "duration_seconds": dur,
                "crashes": 0 if passed else 1,
                "redos_violations": 0,
                "passed": passed,
            }
        )

    if not results:
        raise ValueError(
            f"Unknown fuzz target: '{target}'. Choose from 'all', 'sanitizer', 'proto', 'owasp'."
        )

    return results


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


def main() -> int:
    """CLI entrypoint for fuzz-run command."""
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

    args = parser.parse_args()
    try:
        results = run_target_fuzz(
            target=args.target, runs=args.runs, engine=args.engine
        )
        return display_fuzz_results(results)
    except Exception as exc:
        console.print(f"[bold red]Fuzz runner error:[/bold red] {exc}")
        return 1


__all__ = [
    "display_fuzz_results",
    "main",
    "run_target_fuzz",
]
