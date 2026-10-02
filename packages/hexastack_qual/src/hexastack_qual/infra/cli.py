"""Command-line interface subcommands for hexastack-qual.

Notes/Architectural Intent:
    Provides Typer CLI entrypoints for running quality checks, statement formatting,
    mutation audits, and launching the quality MCP server.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer

from hexastack_qual.adapters.hexaqual.runner import HexaqualRunnerAdapter

app = typer.Typer(
    name="qual",
    help="Quality, governance, and architectural compliance commands.",
    no_args_is_help=True,
)


@app.command("check")
def check(
    package: Annotated[
        str | None,
        typer.Option("--package", "-p", help="Target package name (e.g. 'core')."),
    ] = None,
    skip_tests: Annotated[
        bool,
        typer.Option(
            "--skip-tests/--no-skip-tests", help="Skip long-running unit test suites."
        ),
    ] = True,
) -> None:
    """Execute quality sanity checks across target component or workspace."""
    runner = HexaqualRunnerAdapter()
    scorecard = runner.run_sanity(package=package, skip_tests=skip_tests)

    for check_res in scorecard.checks:
        icon = "✅" if check_res.status == "pass" else "❌"
        typer.echo(f"{icon} {check_res.check_name}: {check_res.details}")

    if not scorecard.is_healthy:
        raise typer.Exit(code=1)


@app.command("format")
def format_statements(
    package: Annotated[
        str | None,
        typer.Option("--package", "-p", help="Target package name."),
    ] = None,
) -> None:
    """Auto-format and sort __all__ lists across modules."""
    runner = HexaqualRunnerAdapter()
    modified = runner.fix_statements(package=package)
    typer.echo(f"✨ Formatted __all__ statements in {modified} file(s).")


@app.command("mcp")
def serve_mcp() -> None:
    """Launch the Quality MCP server over stdio."""
    from hexastack_qual.adapters.mcp.server import run_quality_mcp_server

    asyncio.run(run_quality_mcp_server())


__all__ = [
    "app",
    "check",
    "format_statements",
    "serve_mcp",
]
