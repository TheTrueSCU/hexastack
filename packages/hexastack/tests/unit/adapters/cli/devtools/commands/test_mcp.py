"""Unit tests for devtools mcp commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.mcp import add_mcp_commands


def test_mcp_command_registration():
    app = typer.Typer()
    if callable(add_mcp_commands):
        add_mcp_commands(app)
    runner = CliRunner()
    res = runner.invoke(app, ["mcp", "--help"])
    assert res.exit_code == 0
