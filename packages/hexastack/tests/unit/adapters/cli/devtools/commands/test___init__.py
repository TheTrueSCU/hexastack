"""Unit tests for devtools commands root module."""

import typer

from hexastack.adapters.cli.devtools.commands import add_db_commands


def test_devtools_commands_exports():
    app = typer.Typer()
    add_db_commands(app)
    assert app is not None
