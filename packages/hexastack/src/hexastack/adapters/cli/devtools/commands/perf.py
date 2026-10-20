"""CLI command definitions for performance profiling, stress testing, and microbenchmarks.

Notes/Architectural Intent:
    Unified performance tooling namespace aggregating CPU flamegraphs (py-spy),
    memory flamegraphs (memray), distributed load testing (Locust), and
    microbenchmarking (pytest-benchmark via hexaqual).
"""

from __future__ import annotations

import typer

from hexastack.adapters.cli.devtools.commands.profiling import (
    add_load_command,
    add_profile_command,
)

__all__ = [
    "add_perf_commands",
]


def add_perf_commands(app: typer.Typer) -> None:
    """Register 'perf' CLI command group aggregating profile, load, and bench.

    Args:
        app: Target Typer application instance.

    Notes/Architectural Intent:
        Groups performance and diagnostics tools under a clean, unified namespace.
    """
    perf_app = typer.Typer(
        name="perf",
        help="Performance engineering: profiling, load testing, and microbenchmarks.",
        no_args_is_help=True,
    )
    app.add_typer(perf_app, name="perf")

    # Mount profile (cpu, mem) under perf
    add_profile_command(perf_app)

    # Mount load (Locust) under perf
    add_load_command(perf_app)

    @perf_app.command(
        name="bench",
        help="Execute microbenchmarks via hexaqual test bench (pytest-benchmark).",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def bench_command(
        ctx: typer.Context,
        package: list[str] | None = typer.Option(
            None, "-p", "--package", help="Target package(s)."
        ),
        all_packages: bool = typer.Option(
            False, "-a", "--all", help="Run benchmarks across all workspace packages."
        ),
        smoke: bool = typer.Option(
            False,
            "--smoke",
            help="Smoke mode: run each benchmark once without timing cycles.",
        ),
    ) -> None:
        """Forward benchmark execution to hexaqual test bench."""
        from hexaqual.adapters.code_analysis.pytest_runner import run_main

        argv = ["--bench"]
        if package:
            for p in package:
                argv.extend(["-p", p])
        if all_packages:
            argv.append("-a")
        if smoke:
            argv.append("--smoke")
        if ctx.args:
            argv.extend(ctx.args)
        code = run_main(argv) or 0
        if code != 0:
            raise typer.Exit(code=code)
