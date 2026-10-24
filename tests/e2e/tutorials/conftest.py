"""Shared pytest fixtures and event loop harnesses for E2E CLI tutorials."""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
import typer
from hexaflow import Workflow
from hexaqual.adapters.testing.narrator import CliNarrator

import hexastack.adapters.cli as cli_module
import hexastack.application.diagnostics as diag_module
from hexastack.adapters.cli.devtools.commands import (
    add_db_commands,
    add_dev_command,
    add_fastapi_commands,
    add_grpc_commands,
    add_mcp_commands,
    add_outbox_commands,
    add_serve_command,
    add_ui_commands,
)
from hexastack.adapters.cli.scaffolding.commands import add_scaffold_commands
from hexastack_core.infra.bootstrap import bootstrap


def build_tutorial_cli_app() -> typer.Typer:
    """Construct a composite Typer application with all Hexastack developer commands.

    Returns:
        Configured Typer application containing scaffolding, database, gRPC, and UI commands.

    Notes/Architectural Intent:
        Aggregates driving CLI adapters across the workspace packages and bootstraps
        diagnostics query models so inspection and devtools run in-memory within
        CliNarrator without subprocess overhead.
    """
    result = bootstrap(packages_to_scan=[diag_module, cli_module])
    app = result.get("cli_app")
    if app is None:
        app = typer.Typer(name="hexastack")

    add_scaffold_commands(app)
    add_serve_command(app)
    add_dev_command(app)
    add_ui_commands(app)
    add_db_commands(app)
    add_fastapi_commands(app)
    add_grpc_commands(app)
    add_mcp_commands(app)
    add_outbox_commands(app)
    return app


def run_workflow_safely(wf: Workflow) -> Any:
    """Execute workflow synchronously, offloading to thread pool if event loop is running.

    Args:
        wf: Hexaflow workflow to execute.

    Returns:
        WorkflowExecutionState result from running the workflow.

    Notes/Architectural Intent:
        Prevents 'RuntimeError: asyncio.run() cannot be called from a running event loop'
        when tests are run inside pytest-asyncio auto-managed test event loops.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(wf.run).result()
    return wf.run()


def simulate_workflow_safely(wf: Workflow) -> Any:
    """Execute workflow dry-run simulation, offloading to thread pool if event loop is running.

    Args:
        wf: Hexaflow workflow to simulate.

    Returns:
        WorkflowExecutionState result from simulating the workflow.

    Notes/Architectural Intent:
        Prevents event loop re-entrance errors during dry-run simulation in pytest-asyncio suites.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(wf.simulate).result()
    return wf.simulate()


@pytest.fixture(scope="session")
def tutorial_cli_app() -> typer.Typer:
    """Provide a session-scoped composite Typer CLI application for tutorial narration.

    Returns:
        Configured Typer application with all developer CLI subcommands registered.
    """
    return build_tutorial_cli_app()


@pytest.fixture
def temp_workdir() -> Generator[Path]:
    """Provide an isolated temporary working directory with automatic chdir restoration.

    Yields:
        Path to the temporary directory.

    Notes/Architectural Intent:
        Ensures tutorial scaffolding and file creation cannot pollute the repository working tree
        and guarantees directory state restoration even upon test assertion failures.
    """
    orig_cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        work_path = Path(tmpdir)
        os.chdir(work_path)
        try:
            yield work_path
        finally:
            os.chdir(orig_cwd)


@pytest.fixture
def cli_narrator_factory(
    tutorial_cli_app: typer.Typer,
    temp_workdir: Path,
) -> Generator[Callable[[str], CliNarrator]]:
    """Provide a factory fixture creating CliNarrator instances with auto-finish in demo mode.

    Args:
        tutorial_cli_app: Session-scoped bootstrapped composite Typer CLI application.
        temp_workdir: Isolated temporary working directory.

    Yields:
        Callable taking an output name string and returning a configured CliNarrator.

    Notes/Architectural Intent:
        Standardizes CLI narrator configuration across all tutorial journey tests, ensuring
        assets are consistently written to 'docs/assets/demos' and finalized if RECORD_DEMO=1.
    """
    repo_root = Path(__file__).resolve().parents[3]
    output_dir = repo_root / "docs" / "assets" / "demos"
    demo_active = os.environ.get("RECORD_DEMO") == "1"
    narrators: list[CliNarrator] = []

    def _create_narrator(output_name: str) -> CliNarrator:
        narrator = CliNarrator(
            app=tutorial_cli_app,
            output_name=output_name,
            output_dir=output_dir,
        )
        narrators.append(narrator)
        return narrator

    yield _create_narrator

    if demo_active:
        for narrator in narrators:
            narrator.finish()


@pytest.fixture
def run_workflow() -> Callable[[Workflow], Any]:
    """Provide callable executing a Hexaflow workflow safely across event loop environments.

    Returns:
        Callable executing workflow safely.
    """
    return run_workflow_safely


@pytest.fixture
def simulate_workflow() -> Callable[[Workflow], Any]:
    """Provide callable simulating a Hexaflow workflow safely across event loop environments.

    Returns:
        Callable simulating workflow safely.
    """
    return simulate_workflow_safely


__all__ = [
    "build_tutorial_cli_app",
    "cli_narrator_factory",
    "run_workflow",
    "run_workflow_safely",
    "simulate_workflow",
    "simulate_workflow_safely",
    "temp_workdir",
    "tutorial_cli_app",
]
