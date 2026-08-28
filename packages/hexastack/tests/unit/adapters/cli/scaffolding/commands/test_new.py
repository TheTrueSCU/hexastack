"""Unit tests for 'hexastack new' subcommands."""

import tempfile
from pathlib import Path

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.scaffolding.commands.new import create_new_app


def test_new_app_commands():
    app = typer.Typer()
    new_app = create_new_app()
    app.add_typer(new_app, name="new")
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        orig = Path.cwd()
        try:
            os.chdir(tmpdir)
            # 1. minimal
            res = runner.invoke(app, ["new", "minimal", "min-svc"])
            assert res.exit_code == 0
            assert Path(tmpdir, "min-svc", "pyproject.toml").exists()

            # 2. web-api
            res = runner.invoke(app, ["new", "web-api", "web-svc", "--db", "sqlite"])
            assert res.exit_code == 0
            assert Path(tmpdir, "web-svc", "pyproject.toml").exists()

            # 3. event-driven
            res = runner.invoke(app, ["new", "event-driven", "event-svc"])
            assert res.exit_code == 0
            assert Path(tmpdir, "event-svc", "pyproject.toml").exists()

            # 4. mcp-agent
            res = runner.invoke(app, ["new", "mcp-agent", "mcp-svc"])
            assert res.exit_code == 0
            assert Path(tmpdir, "mcp-svc", "pyproject.toml").exists()

            # 5. grpc-service
            res = runner.invoke(app, ["new", "grpc-service", "grpc-svc"])
            assert res.exit_code == 0
            assert Path(tmpdir, "grpc-svc", "pyproject.toml").exists()

            # 6. graphql-service
            res = runner.invoke(app, ["new", "graphql-service", "gql-svc"])
            assert res.exit_code == 0
            assert Path(tmpdir, "gql-svc", "pyproject.toml").exists()

            # 7. enterprise
            res = runner.invoke(app, ["new", "enterprise", "ent-svc"])
            assert res.exit_code == 0
            assert Path(tmpdir, "ent-svc", "pyproject.toml").exists()
        finally:
            os.chdir(orig)
