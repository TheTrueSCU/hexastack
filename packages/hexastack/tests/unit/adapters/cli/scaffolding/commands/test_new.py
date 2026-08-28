"""Unit tests for 'hexastack new' subcommands."""

import tempfile
from pathlib import Path

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.scaffolding.commands.new import create_new_app


def test_new_app_commands():
    app = typer.Typer()
    new_app = create_new_app()
    app.add_typer(new_app, name="new")
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        orig = Path.cwd()
        try:
            os.chdir(tmpdir)
            res = runner.invoke(app, ["new", "web-api", "order-svc"])
            assert res.exit_code == 0
            assert Path(tmpdir, "order-svc", "pyproject.toml").exists()
        finally:
            os.chdir(orig)
