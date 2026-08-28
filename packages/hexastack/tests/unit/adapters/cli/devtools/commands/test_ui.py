"""Unit tests for devtools ui commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.ui import add_ui_commands


def test_ui_command_registration():
    app = typer.Typer()
    if callable(add_ui_commands):
        add_ui_commands(app)
    runner = CliRunner()
    res = runner.invoke(app, ["ui", "--help"])
    assert res.exit_code == 0
