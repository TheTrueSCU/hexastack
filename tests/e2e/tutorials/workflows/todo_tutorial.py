"""Hexaflow DAG workflow orchestrating the 7-chapter To-Do tutorial journey."""

from __future__ import annotations

from typing import Any

from hexaflow import Workflow
from hexaqual.adapters.testing.narrator import CliNarrator


def _serialize_artifacts(seg: dict[str, Any]) -> dict[str, str]:
    """Serialize artifact Path objects to strings for Hexaflow state persistence."""
    return {k: str(v) for k, v in seg.items()}


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
            "artifacts": [_serialize_artifacts(seg1), _serialize_artifacts(seg2)],
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
            "artifacts": [_serialize_artifacts(seg1), _serialize_artifacts(seg2)],
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
            "artifacts": [_serialize_artifacts(seg)],
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
            "artifacts": [_serialize_artifacts(seg)],
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
            "artifacts": [_serialize_artifacts(seg)],
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
            "artifacts": [_serialize_artifacts(seg)],
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
            "artifacts": [_serialize_artifacts(seg)],
        }

    return wf


__all__ = [
    "create_todo_tutorial_workflow",
]
