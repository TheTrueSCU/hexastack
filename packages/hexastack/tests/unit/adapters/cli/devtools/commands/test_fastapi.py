"""Unit tests for devtools fastapi commands."""

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.fastapi import add_fastapi_commands


def test_fastapi_commands():
    app = typer.Typer()
    add_fastapi_commands(app)
    runner = CliRunner()
    res = runner.invoke(app, ["fastapi", "--help"])
    assert res.exit_code == 0
    res_routes = runner.invoke(app, ["fastapi", "routes"])
    assert res_routes.exit_code == 0
