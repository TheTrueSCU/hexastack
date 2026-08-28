"""Unit tests for devtools dev commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.dev import add_dev_command


def test_dev_command_registration():
    app = typer.Typer()
    if callable(add_dev_command):
        add_dev_command(app)
    runner = CliRunner()
    res = runner.invoke(app, ["dev", "--help"])
    assert res.exit_code == 0
