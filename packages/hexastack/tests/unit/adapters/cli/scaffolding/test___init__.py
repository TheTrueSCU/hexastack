"""Unit tests for scaffolding CLI adapter initializer."""

from unittest.mock import patch

import typer

from hexastack.adapters.cli.scaffolding import add_scaffold_commands


def test_add_scaffold_commands():
    app = typer.Typer()
    with (
        patch("hexastack.adapters.cli.scaffolding.create_new_app") as mock_new,
        patch("hexastack.adapters.cli.scaffolding.add_init_command") as mock_init,
    ):
        mock_new.return_value = typer.Typer()
        add_scaffold_commands(app)
        assert mock_new.called
        assert mock_init.called
