"""Unit tests for devtools grpc commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.grpc import add_grpc_commands


def test_grpc_command_registration():
    app = typer.Typer()
    if callable(add_grpc_commands):
        add_grpc_commands(app)
    runner = CliRunner()
    res = runner.invoke(app, ["grpc", "--help"])
    assert res.exit_code == 0
