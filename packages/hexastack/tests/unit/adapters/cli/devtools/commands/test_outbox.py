"""Unit tests for devtools outbox commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.outbox import add_outbox_commands


def test_outbox_command_registration():
    app = typer.Typer()
    if callable(add_outbox_commands):
        add_outbox_commands(app)
    runner = CliRunner()
    res = runner.invoke(app, ["outbox", "--help"])
    assert res.exit_code == 0
