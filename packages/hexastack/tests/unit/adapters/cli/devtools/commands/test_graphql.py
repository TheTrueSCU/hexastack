"""Unit tests for devtools graphql commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.graphql import add_graphql_commands


def test_graphql_commands():
    app = typer.Typer()
    add_graphql_commands(app)
    runner = CliRunner()

    res = runner.invoke(app, ["graphql", "--help"])
    assert res.exit_code == 0

    res_schema = runner.invoke(app, ["graphql", "schema"])
    assert res_schema.exit_code == 0
