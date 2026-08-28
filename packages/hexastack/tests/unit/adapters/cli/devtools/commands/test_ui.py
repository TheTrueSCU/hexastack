"""Unit tests for devtools ui commands."""

from unittest.mock import patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.ui import add_ui_commands


def test_ui_commands():
    app = typer.Typer()
    add_ui_commands(app)
    runner = CliRunner()

    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0

    with patch("uvicorn.run"):
        res_open = runner.invoke(app, ["--no-reload"])
        assert res_open.exit_code == 0
