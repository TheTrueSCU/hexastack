"""Unit tests for devtools serve commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.serve import add_serve_command


def test_serve_command_registration():
    app = typer.Typer()
    if callable(add_serve_command):
        add_serve_command(app)
    runner = CliRunner()
    res = runner.invoke(app, ["serve", "--help"])
    assert res.exit_code == 0
