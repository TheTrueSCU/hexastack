"""Unit tests for 'hexastack init' CLI command."""

from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from hexastack.adapters.cli.scaffolding.commands.init import add_init_command


def test_init_command(tmp_path):
    """Verify init command execution in non-interactive and interactive modes."""
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
        patch("questionary.text") as mock_text,
        patch("questionary.select") as mock_select,
        patch("questionary.checkbox") as mock_checkbox,
    ):
        text_prompt = MagicMock()
        text_prompt.ask.return_value = "wizard_proj"
        mock_text.return_value = text_prompt

        select_prompt = MagicMock()
        select_prompt.ask.side_effect = ["enterprise", "postgres"]
        mock_select.return_value = select_prompt

        checkbox_prompt = MagicMock()
        checkbox_prompt.ask.return_value = [
            "qual",
            "agents",
            "mutation",
            "release",
            "openssf",
        ]
        mock_checkbox.return_value = checkbox_prompt

        mock_scaffold.return_value = tmp_path / "wizard_proj"
        res_wiz = runner.invoke(app, ["--interactive"])
        assert res_wiz.exit_code == 0
        assert mock_scaffold.called

    with patch(
        "hexastack.adapters.cli.scaffolding.commands.init.scaffold_project",
        side_effect=FileExistsError("Target directory already exists."),
    ):
        res_err = runner.invoke(
            app,
            [
                "--name",
                "existing_project",
                "--template",
                "minimal",
                "--db",
                "in-memory",
            ],
        )
        assert res_err.exit_code == 1
        assert "Initialization failed" in res_err.output
