"""Unit tests for demo CLI commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.demo.commands import (
    add_db_commands,
    add_grpc_commands,
    add_mcp_commands,
    add_serve_command,
    add_ui_commands,
)


def test_add_demo_commands_registration():
    """Verify demo subcommands register on Typer instance without error."""
    app = typer.Typer()
    add_db_commands(app)
    add_grpc_commands(app)
    add_mcp_commands(app)
    add_ui_commands(app)
    add_serve_command(app)

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "db" in result.output or "serve" in result.output
