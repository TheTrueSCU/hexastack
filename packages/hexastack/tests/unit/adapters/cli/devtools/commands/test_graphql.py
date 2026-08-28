"""Unit tests for devtools graphql commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.graphql import add_graphql_commands


def test_graphql_command_registration():
    app = typer.Typer()
    if callable(add_graphql_commands):
        add_graphql_commands(app)
    runner = CliRunner()
    res = runner.invoke(app, ["graphql", "--help"])
    assert res.exit_code == 0
