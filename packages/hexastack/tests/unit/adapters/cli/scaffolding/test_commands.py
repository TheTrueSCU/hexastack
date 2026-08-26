"""Unit tests for umbrella CLI commands and scaffolding subcommands."""

import tempfile
from pathlib import Path

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli import add_scaffold_commands


def test_cli_scaffold_subcommands():
    """Verify 'new web-api', 'new minimal', and 'init' subcommands generate projects."""
    app = typer.Typer()
    add_scaffold_commands(app)
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        orig_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)

            # Test `new web-api` subcommand
            result = runner.invoke(
                app, ["new", "web-api", "billing-service", "--db", "sqlite"]
            )
            assert result.exit_code == 0
            assert "Created new Hexastack Web API project" in result.output
            assert Path(tmpdir, "billing-service", "pyproject.toml").exists()

            # Test `new minimal` subcommand
            result_min = runner.invoke(app, ["new", "minimal", "worker-service"])
            assert result_min.exit_code == 0
            assert "Created new Minimal Hexastack project" in result_min.output
            assert Path(tmpdir, "worker-service", "pyproject.toml").exists()

            # Test `new grpc-service` subcommand
            result_grpc = runner.invoke(app, ["new", "grpc-service", "rpc-service"])
            assert result_grpc.exit_code == 0
            assert "Created new gRPC Hexastack project" in result_grpc.output
            assert Path(
                tmpdir,
                "rpc-service",
                "src",
                "rpc_service",
                "adapters",
                "driving",
                "grpc.py",
            ).exists()

            # Test `new event-driven` subcommand
            result_events = runner.invoke(app, ["new", "event-driven", "order-service"])
            assert result_events.exit_code == 0
            assert "Created new Event-Driven Hexastack project" in result_events.output
            assert Path(tmpdir, "order-service", "pyproject.toml").exists()

            # Test `new mcp-agent` subcommand
            result_mcp = runner.invoke(app, ["new", "mcp-agent", "agent-service"])
            assert result_mcp.exit_code == 0
            assert "Created new MCP Agent Hexastack project" in result_mcp.output
            assert Path(tmpdir, "agent-service", "pyproject.toml").exists()

            # Test `new enterprise` subcommand
            result_ent = runner.invoke(app, ["new", "enterprise", "fintech-core"])
            assert result_ent.exit_code == 0
            assert "Created new Full-Featured Enterprise Hexastack project" in result_ent.output
            assert Path(tmpdir, "fintech-core", "pyproject.toml").exists()

            # Test `init` command
            init_dir = Path(tmpdir, "init-test-app")
            init_dir.mkdir()
            os.chdir(init_dir)
            result_init = runner.invoke(app, ["init", "--name", "init-test-app", "--template", "minimal", "--db", "sqlite"])
            assert result_init.exit_code == 0
            assert "Initialized Hexastack project" in result_init.output
            assert Path(init_dir, "pyproject.toml").exists()
        finally:
            os.chdir(orig_cwd)
