"""Unit tests for devtools serve commands."""

from unittest.mock import patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.serve import add_serve_command


def test_serve_commands():
    app = typer.Typer()
    add_serve_command(app)
    runner = CliRunner()

    res = runner.invoke(app, ["--help"], color=False)
    assert res.exit_code == 0
    assert "--host" in res.output

    with patch("uvicorn.run"):
        res_run = runner.invoke(app, ["--no-reload"])
        assert res_run.exit_code == 0

    with patch("importlib.util.find_spec", return_value=None):
        import pytest

        from hexastack_core.domain.exceptions import MissingDependencyError

        with pytest.raises(MissingDependencyError):
            runner.invoke(app, [], catch_exceptions=False)
