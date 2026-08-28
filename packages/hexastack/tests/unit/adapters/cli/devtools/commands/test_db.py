"""Unit tests for devtools db commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.db import add_db_commands


def test_db_command_registration():
    app = typer.Typer()
    if callable(add_db_commands):
        add_db_commands(app)
    runner = CliRunner()
    res = runner.invoke(app, ["db", "--help"])
    assert res.exit_code == 0
