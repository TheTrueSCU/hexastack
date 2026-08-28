"""Unit tests for 'hexastack init' command."""

import tempfile
from pathlib import Path

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.scaffolding.commands.init import add_init_command


def test_init_command():
    app = typer.Typer()
    add_init_command(app)
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        orig = Path.cwd()
        try:
            init_dir = Path(tmpdir, "my-app")
            init_dir.mkdir()
            os.chdir(init_dir)
            res = runner.invoke(app, ["--name", "my-app", "--template", "minimal"])
            assert res.exit_code == 0
            assert Path(init_dir, "pyproject.toml").exists()
        finally:
            os.chdir(orig)
