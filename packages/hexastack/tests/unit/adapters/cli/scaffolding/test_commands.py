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

            # Test `new graphql-service` subcommand
            result_gql = runner.invoke(
                app, ["new", "graphql-service", "gateway-service"]
            )
            assert result_gql.exit_code == 0
            assert "Created new GraphQL Hexastack project" in result_gql.output
            assert Path(
                tmpdir,
                "gateway-service",
                "src",
                "gateway_service",
                "adapters",
                "driving",
                "graphql.py",
            ).exists()
        finally:
            os.chdir(orig_cwd)
