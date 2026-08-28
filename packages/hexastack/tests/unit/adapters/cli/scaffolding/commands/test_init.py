"""Unit tests for 'hexastack init' CLI command."""

from unittest.mock import patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.scaffolding.commands.init import add_init_command


def test_init_command(tmp_path):
    app = typer.Typer()
    add_init_command(app)
    runner = CliRunner()

    res_help = runner.invoke(app, ["--help"])
    assert res_help.exit_code == 0

    with patch(
        "hexastack.adapters.cli.scaffolding.commands.init.scaffold_project"
    ) as mock_scaffold:
        mock_scaffold.return_value = tmp_path / "my_project"
        res_exec = runner.invoke(
            app, ["--name", "my_project", "--template", "minimal", "--db", "in-memory"]
        )
        assert res_exec.exit_code == 0
        assert mock_scaffold.called

    with (
        patch(
            "hexastack.adapters.cli.scaffolding.commands.init.scaffold_project"
        ) as mock_scaffold,
        patch(
            "rich.prompt.Prompt.ask",
            side_effect=["wizard_proj", "enterprise", "postgres"],
        ),
        patch("rich.prompt.Confirm.ask", side_effect=[True, True, True, True]),
    ):
        mock_scaffold.return_value = tmp_path / "wizard_proj"
        res_wiz = runner.invoke(app, ["--interactive"])
        assert res_wiz.exit_code == 0
