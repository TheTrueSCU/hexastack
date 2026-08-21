"""Unit tests for demo CLI commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.demo.commands import (
    add_db_commands,
    add_fastapi_commands,
    add_graphql_commands,
    add_grpc_commands,
    add_mcp_commands,
    add_outbox_commands,
    add_serve_command,
    add_ui_commands,
)


def test_add_demo_commands_registration():
    """Verify demo subcommands register on Typer instance without error."""
    app = typer.Typer()
    add_db_commands(app)
    add_fastapi_commands(app)
    add_graphql_commands(app)
    add_grpc_commands(app)
    add_mcp_commands(app)
    add_outbox_commands(app)
    add_ui_commands(app)
    add_serve_command(app)

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "fastapi" in result.output
    assert "grpc" in result.output
    assert "mcp" in result.output
    assert "outbox" in result.output

    # Test reflection / list commands
    grpc_list_res = runner.invoke(app, ["grpc", "list"])
    assert grpc_list_res.exit_code == 0

    mcp_list_res = runner.invoke(app, ["mcp", "list"])
    assert mcp_list_res.exit_code == 0
    assert "Model Context Protocol" in mcp_list_res.output

    relay_result = runner.invoke(app, ["outbox", "relay", "--once"])
    assert relay_result.exit_code == 0
    assert "Drained and published 0 pending outbox events" in relay_result.output
