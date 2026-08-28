"""Unit tests for devtools profiling commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.profiling import add_profile_command


def test_profiling_command_registration():
    app = typer.Typer()
    if callable(add_profile_command):
        add_profile_command(app)
    runner = CliRunner()
    res = runner.invoke(app, ["profile", "--help"])
    assert res.exit_code == 0
