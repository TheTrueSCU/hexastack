"""Unit tests for devtools profiling commands."""

from unittest.mock import patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.devtools.commands.profiling import (
    add_load_command,
    add_profile_command,
)


def test_profiling_commands():
    app = typer.Typer()
    add_profile_command(app)
    add_load_command(app)
    runner = CliRunner()

    res_profile = runner.invoke(app, ["profile", "--help"], color=False)
    assert res_profile.exit_code == 0
    assert "cpu" in res_profile.output
    assert "memory" in res_profile.output

    with (
        patch("importlib.util.find_spec", return_value=True),
        patch("subprocess.run") as mock_sub,
    ):
        mock_sub.return_value.returncode = 0
        res_cpu = runner.invoke(app, ["profile", "cpu", "--pid", "12345"])
        assert res_cpu.exit_code == 0

        res_cpu_fail = runner.invoke(app, ["profile", "cpu"])
        assert res_cpu_fail.exit_code == 1

        with patch("pathlib.Path.exists", return_value=True):
            res_mem = runner.invoke(app, ["profile", "memory"])
            assert res_mem.exit_code == 0

        with patch("pathlib.Path.exists", return_value=False):
            res_mem_missing = runner.invoke(app, ["profile", "memory"])
            assert res_mem_missing.exit_code == 1

        res_load = runner.invoke(app, ["load", "--help"], color=False)
        assert res_load.exit_code == 0

        res_load_exec = runner.invoke(
            app, ["load", "--users", "10", "--run-time", "5s"]
        )
        assert res_load_exec.exit_code == 0
