"""Unit tests for demo CLI commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands import (
    add_db_commands,
    add_dev_command,
    add_fastapi_commands,
    add_graphql_commands,
    add_grpc_commands,
    add_load_command,
    add_mcp_commands,
    add_outbox_commands,
    add_profile_command,
    add_serve_command,
    add_ui_commands,
)


def test_add_demo_commands_registration():
    """Verify demo subcommands register on Typer instance without error."""
    app = typer.Typer()
    add_db_commands(app)
    add_dev_command(app)
    add_fastapi_commands(app)
    add_graphql_commands(app)
    add_grpc_commands(app)
    add_mcp_commands(app)
    add_outbox_commands(app)
    add_ui_commands(app)
    add_serve_command(app)
    add_profile_command(app)
    add_load_command(app)

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "dev" in result.output
    assert "fastapi" in result.output
    assert "grpc" in result.output
    assert "mcp" in result.output
    assert "outbox" in result.output
    assert "profile" in result.output
    assert "load" in result.output

    # Test reflection / list commands
    grpc_list_res = runner.invoke(app, ["grpc", "list"])
    assert grpc_list_res.exit_code == 0

    mcp_list_res = runner.invoke(app, ["mcp", "list"])
    assert mcp_list_res.exit_code == 0
    assert "Model Context Protocol" in mcp_list_res.output

    relay_result = runner.invoke(app, ["outbox", "relay", "--once"])
    assert relay_result.exit_code == 0
    assert "Drained and published 0 pending outbox events" in relay_result.output

    # Test fastapi routes inspection
    fastapi_res = runner.invoke(app, ["fastapi", "routes"])
    assert fastapi_res.exit_code == 0

    # Test db subcommands
    db_help = runner.invoke(app, ["db", "--help"])
    assert db_help.exit_code == 0
    assert "init" in db_help.output
    assert "revision" in db_help.output

    # Test profile & load help
    profile_help = runner.invoke(app, ["profile", "--help"], color=False)
    assert profile_help.exit_code == 0
    assert "cpu" in profile_help.output
    assert "memory" in profile_help.output

    load_help = runner.invoke(app, ["load", "--help"], color=False)
    assert load_help.exit_code == 0
    assert "users" in load_help.output or "--users" in load_help.output

    # Test MCP config generation
    mcp_cfg_res = runner.invoke(app, ["mcp", "config", "-c", "claude"])
    assert mcp_cfg_res.exit_code == 0
    assert "mcpServers" in mcp_cfg_res.output

    # Test GraphQL schema command
    gql_res = runner.invoke(app, ["graphql", "schema"])
    assert gql_res.exit_code == 0
    assert "DefaultQuery" in gql_res.output

    # Test UI help
    ui_help = runner.invoke(app, ["ui", "--help"])
    assert ui_help.exit_code == 0

    # Test serve help
    serve_help = runner.invoke(app, ["serve", "--help"])
    assert serve_help.exit_code == 0

    # Test grpc compile with mocked compiler backend
    from unittest.mock import patch

    with patch(
        "hexastack_grpc.infra.compiler.ProtoCompiler.compile_files", return_value=[]
    ):
        grpc_compile_res = runner.invoke(app, ["grpc", "compile"])
        assert grpc_compile_res.exit_code == 0
