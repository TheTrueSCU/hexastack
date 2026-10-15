"""End-to-end demo and verification test for To-Do tutorial journey Hexaflow workflow."""

from __future__ import annotations

import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
import typer
from hexaflow import Workflow, WorkflowStatus

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
from hexastack_cli.testing.narrator import CliNarrator
from hexastack_core.infra.bootstrap import bootstrap


def build_todo_cli_app() -> typer.Typer:
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


def create_todo_tutorial_workflow(narrator: CliNarrator | None = None) -> Workflow:
    """Create a unified Hexaflow DAG orchestrating the 7-chapter To-Do tutorial journey.

    Args:
        narrator: Configured CliNarrator instance capturing terminal events and subtitles,
            or None when constructing the DAG solely for simulation or topology introspection.

    Returns:
        Hexaflow Workflow instance with sequential dependency stages and checkpoint slicing.

    Notes/Architectural Intent:
        Consolidates the 7 tutorial chapters into an atomic, stateful DAG. Unlike
        legacy isolated pytest files that replayed all prior chapters silently (O(N^2)
        overhead), the DAG shares filesystem and database state continuously across stages,
        flushing checkpoint segments at each milestone for true-timing video and VTT generation.
    """
    wf = Workflow(name="todo-tutorial-journey", version="1.0.0")

    def _require_narrator() -> CliNarrator:
        if narrator is None:
            raise RuntimeError(
                "CliNarrator is required to execute tutorial workflow steps"
            )
        return narrator

    @wf.step(
        name="step_ch01_scaffolding",
        description="Chapter 1: Scaffolding a To-Do REST microservice & inspecting hexagonal layout",
        dry_run=lambda: {"chapter": 1, "status": "dry_run"},
    )
    def step_ch01_scaffolding() -> dict[str, Any]:
        """Execute Chapter 1 scaffolding and hexagonal layout inspection."""
        cli = _require_narrator()
        cli.step("Tutorial Chapter 1: Scaffolding a To-Do REST microservice")
        res1 = cli.run_command(
            ["new", "web-api", "todo-app", "--db", "in-memory"],
            record=True,
        )
        if res1.exit_code != 0:
            raise RuntimeError(
                f"Ch 1 Step 1 failed with exit code {res1.exit_code}: {res1.output}"
            )
        seg1 = cli.checkpoint_segment("ch01-cli-demo-part1-scaffolding")

        cli.step("Inspecting pure hexagonal architecture layout")
        res2 = cli.run_command(["new", "--help"], record=True)
        if res2.exit_code != 0:
            raise RuntimeError(
                f"Ch 1 Step 2 failed with exit code {res2.exit_code}: {res2.output}"
            )
        cli.step("Project scaffolded with zero external dependencies")
        seg2 = cli.checkpoint_segment("ch01-cli-demo-part2-layout")

        return {
            "chapter": 1,
            "status": "completed",
            "segments": ["part1-scaffolding", "part2-layout"],
            "artifacts": [seg1, seg2],
        }

    @wf.step(
        name="step_ch02_sqlite_persistence",
        depends_on=["step_ch01_scaffolding"],
        description="Chapter 2: Adding SQLite persistence and Alembic database migrations",
        dry_run=lambda step_ch01_scaffolding=None: {"chapter": 2, "status": "dry_run"},
    )
    def step_ch02_sqlite_persistence(
        step_ch01_scaffolding: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Chapter 2 SQLite persistence scaffolding and migration inspection."""
        cli = _require_narrator()
        cli.step("Tutorial Chapter 2: Adding SQLite persistence & migrations")
        res1 = cli.run_command(
            ["new", "web-api", "todo-sqlite-app", "--db", "sqlite"],
            record=True,
        )
        if res1.exit_code != 0:
            raise RuntimeError(
                f"Ch 2 Step 1 failed with exit code {res1.exit_code}: {res1.output}"
            )
        seg1 = cli.checkpoint_segment("ch02-cli-demo-part1-sqlite")

        cli.step("Inspecting Alembic database migration commands")
        res2 = cli.run_command(["db", "--help"], record=True)
        if res2.exit_code != 0:
            raise RuntimeError(
                f"Ch 2 Step 2 failed with exit code {res2.exit_code}: {res2.output}"
            )
        cli.step("SQLite persistence and migration engine configured")
        seg2 = cli.checkpoint_segment("ch02-cli-demo-part2-migrations")

        return {
            "chapter": 2,
            "status": "completed",
            "segments": ["part1-sqlite", "part2-migrations"],
            "artifacts": [seg1, seg2],
        }

    @wf.step(
        name="step_ch03_jwt_rbac",
        depends_on=["step_ch02_sqlite_persistence"],
        description="Chapter 3: Role-Based Access Control (RBAC) & JWT authentication",
        dry_run=lambda step_ch02_sqlite_persistence=None: {
            "chapter": 3,
            "status": "dry_run",
        },
    )
    def step_ch03_jwt_rbac(
        step_ch02_sqlite_persistence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Chapter 3 RBAC and JWT authentication registry introspection."""
        cli = _require_narrator()
        cli.step("Tutorial Chapter 3: Role-Based Access Control (RBAC) & JWT Auth")
        res = cli.run_command(["inspect", "registry"], record=True)
        if res.exit_code != 0:
            raise RuntimeError(
                f"Ch 3 failed with exit code {res.exit_code}: {res.output}"
            )
        cli.step("JWT authentication and RBAC domain policies enforced")
        seg = cli.checkpoint_segment("ch03-cli-demo")

        return {
            "chapter": 3,
            "status": "completed",
            "segments": ["ch03-cli-demo"],
            "artifacts": [seg],
        }

    @wf.step(
        name="step_ch04_events_outbox",
        depends_on=["step_ch03_jwt_rbac"],
        description="Chapter 4: Event-Driven Architecture with Outbox and CloudEvents",
        dry_run=lambda step_ch03_jwt_rbac=None: {"chapter": 4, "status": "dry_run"},
    )
    def step_ch04_events_outbox(
        step_ch03_jwt_rbac: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Chapter 4 Transactional Outbox inspection."""
        cli = _require_narrator()
        cli.step(
            "Tutorial Chapter 4: Event-Driven Architecture with Outbox & CloudEvents"
        )
        res = cli.run_command(["outbox", "--help"], record=True)
        if res.exit_code != 0:
            raise RuntimeError(
                f"Ch 4 failed with exit code {res.exit_code}: {res.output}"
            )
        cli.step("Transactional outbox and CloudEvents broker configured")
        seg = cli.checkpoint_segment("ch04-cli-demo")

        return {
            "chapter": 4,
            "status": "completed",
            "segments": ["ch04-cli-demo"],
            "artifacts": [seg],
        }

    @wf.step(
        name="step_ch05_ai_mcp",
        depends_on=["step_ch04_events_outbox"],
        description="Chapter 5: Model Context Protocol (MCP) AI Tools and IDE configuration",
        dry_run=lambda step_ch04_events_outbox=None: {
            "chapter": 5,
            "status": "dry_run",
        },
    )
    def step_ch05_ai_mcp(
        step_ch04_events_outbox: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Chapter 5 MCP tooling discovery and client configuration generation."""
        cli = _require_narrator()
        cli.step("Tutorial Chapter 5: Model Context Protocol (MCP) AI Tools")
        res1 = cli.run_command(["mcp", "list"], record=True)
        if res1.exit_code != 0:
            raise RuntimeError(
                f"Ch 5 Step 1 failed with exit code {res1.exit_code}: {res1.output}"
            )

        cli.step("Generating MCP configuration for Gemini and Antigravity IDE")
        res2 = cli.run_command(
            ["mcp", "config", "--client", "antigravity"],
            record=True,
        )
        if res2.exit_code != 0:
            raise RuntimeError(
                f"Ch 5 Step 2 failed with exit code {res2.exit_code}: {res2.output}"
            )
        cli.step("Model Context Protocol tools exposed to AI agents")
        seg = cli.checkpoint_segment("ch05-cli-demo")

        return {
            "chapter": 5,
            "status": "completed",
            "segments": ["ch05-cli-demo"],
            "artifacts": [seg],
        }

    @wf.step(
        name="step_ch06_observability_devtools",
        depends_on=["step_ch05_ai_mcp"],
        description="Chapter 6: Production Observability, OpenTelemetry & DevTools Web UI",
        dry_run=lambda step_ch05_ai_mcp=None: {"chapter": 6, "status": "dry_run"},
    )
    def step_ch06_observability_devtools(
        step_ch05_ai_mcp: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Chapter 6 DevTools and observability launcher inspection."""
        cli = _require_narrator()
        cli.step("Tutorial Chapter 6: Production Observability & Distributed Tracing")
        res = cli.run_command(["ui", "--help"], record=True)
        if res.exit_code != 0:
            raise RuntimeError(
                f"Ch 6 failed with exit code {res.exit_code}: {res.output}"
            )
        cli.step("DevTools visualizer and distributed tracing active")
        seg = cli.checkpoint_segment("ch06-cli-demo")

        return {
            "chapter": 6,
            "status": "completed",
            "segments": ["ch06-cli-demo"],
            "artifacts": [seg],
        }

    @wf.step(
        name="step_ch07_grpc_parity",
        depends_on=["step_ch06_observability_devtools"],
        description="Chapter 7: High-Performance gRPC binary protocol and schema compilation",
        dry_run=lambda step_ch06_observability_devtools=None: {
            "chapter": 7,
            "status": "dry_run",
        },
    )
    def step_ch07_grpc_parity(
        step_ch06_observability_devtools: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute Chapter 7 gRPC service discovery and Protobuf compiler options inspection."""
        cli = _require_narrator()
        cli.step("Tutorial Chapter 7: High-Performance gRPC & Dual Transport Parity")
        res1 = cli.run_command(["grpc", "list"], record=True)
        if res1.exit_code != 0:
            raise RuntimeError(
                f"Ch 7 Step 1 failed with exit code {res1.exit_code}: {res1.output}"
            )

        cli.step("Inspecting in-process Protobuf compiler tooling")
        res2 = cli.run_command(["grpc", "compile", "--help"], record=True)
        if res2.exit_code != 0:
            raise RuntimeError(
                f"Ch 7 Step 2 failed with exit code {res2.exit_code}: {res2.output}"
            )
        cli.step("High-performance gRPC server daemon & reflection active")
        seg = cli.checkpoint_segment("ch07-cli-demo")

        return {
            "chapter": 7,
            "status": "completed",
            "segments": ["ch07-cli-demo"],
            "artifacts": [seg],
        }

    return wf


def _run_workflow_safely(wf: Workflow) -> Any:
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


def _simulate_workflow_safely(wf: Workflow) -> Any:
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


def test_todo_tutorial_workflow_dag_structure() -> None:
    """Validate To-Do tutorial Hexaflow DAG topology, dependencies, and dry-run simulation."""
    wf = create_todo_tutorial_workflow()

    workflow_name = wf.name
    assert workflow_name == "todo-tutorial-journey"

    step_count = len(wf._steps)
    assert step_count == 7

    step_names = [s.name for s in wf._steps]
    expected_steps = [
        "step_ch01_scaffolding",
        "step_ch02_sqlite_persistence",
        "step_ch03_jwt_rbac",
        "step_ch04_events_outbox",
        "step_ch05_ai_mcp",
        "step_ch06_observability_devtools",
        "step_ch07_grpc_parity",
    ]
    assert step_names == expected_steps

    step_by_name = {s.name: s for s in wf._steps}
    ch02_deps = step_by_name["step_ch02_sqlite_persistence"].depends_on
    assert ch02_deps == ("step_ch01_scaffolding",)

    ch07_deps = step_by_name["step_ch07_grpc_parity"].depends_on
    assert ch07_deps == ("step_ch06_observability_devtools",)

    # Validate Mermaid visualization generation
    mermaid_diagram = wf.to_mermaid()
    has_mermaid_nodes = (
        "step_ch01_scaffolding" in mermaid_diagram
        and "step_ch07_grpc_parity" in mermaid_diagram
    )
    assert has_mermaid_nodes is True

    # Validate ASCII tree generation
    ascii_tree = wf.to_ascii()
    has_ascii_nodes = (
        "step_ch01_scaffolding" in ascii_tree and "step_ch07_grpc_parity" in ascii_tree
    )
    assert has_ascii_nodes is True

    # Validate dry-run DAG simulation without executing terminal commands
    sim_res = _simulate_workflow_safely(wf)
    sim_status = sim_res.status
    assert sim_status == WorkflowStatus.COMPLETED

    is_dry_run = sim_res.is_dry_run
    assert is_dry_run is True

    sim_step_count = len(sim_res.step_checkpoints)
    assert sim_step_count == 7


@pytest.mark.demo
def test_todo_tutorial_workflow_execution() -> None:
    """Execute complete 7-chapter To-Do tutorial DAG and record micro-segment video clips."""
    app = build_todo_cli_app()
    repo_root = Path.cwd()
    output_dir = repo_root / "docs" / "assets" / "demos"

    expected_segment_keys = [
        "todo-ch01-cli-demo-part1-scaffolding",
        "todo-ch01-cli-demo-part2-layout",
        "todo-ch02-cli-demo-part1-sqlite",
        "todo-ch02-cli-demo-part2-migrations",
        "todo-ch03-cli-demo",
        "todo-ch04-cli-demo",
        "todo-ch05-cli-demo",
        "todo-ch06-cli-demo",
        "todo-ch07-cli-demo",
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)
            narrator = CliNarrator(
                app,
                output_name="todo",
                output_dir=output_dir,
            )
            wf = create_todo_tutorial_workflow(narrator)

            res = _run_workflow_safely(wf)

            res_status = res.status
            assert res_status == WorkflowStatus.COMPLETED

            segment_count = narrator._segment_count
            assert segment_count == 9

            if os.environ.get("RECORD_DEMO") == "1":
                artifacts = narrator.finish()

                for seg_key in expected_segment_keys:
                    seg_dict = narrator.segments.get(seg_key)
                    has_seg = seg_dict is not None
                    assert has_seg is True
                    assert seg_dict is not None

                    webm_file = seg_dict.get("webm")
                    has_webm = webm_file is not None and webm_file.exists()
                    assert has_webm is True

                    vtt_file = seg_dict.get("vtt")
                    has_vtt = vtt_file is not None and vtt_file.exists()
                    assert has_vtt is True

                    has_webm_artifact = f"{seg_key}_webm" in artifacts
                    assert has_webm_artifact is True
        finally:
            os.chdir(orig_cwd)


__all__ = [
    "build_todo_cli_app",
    "create_todo_tutorial_workflow",
    "test_todo_tutorial_workflow_dag_structure",
    "test_todo_tutorial_workflow_execution",
]
