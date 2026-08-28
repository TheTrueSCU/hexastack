"""Unit tests for devtools fastapi commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.fastapi import add_fastapi_commands


def test_fastapi_command_registration():
    app = typer.Typer()
    if callable(add_fastapi_commands):
        add_fastapi_commands(app)
    runner = CliRunner()
    res = runner.invoke(app, ["fastapi", "--help"])
    assert res.exit_code == 0
