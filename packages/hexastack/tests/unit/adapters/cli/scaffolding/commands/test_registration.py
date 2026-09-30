"""Unit tests for scaffolding CLI command registration.

Notes/Architectural Intent:
    Ensures that project scaffolding commands (`new` and `init`) are correctly
    registered and mounted onto the root Typer application.
"""

from unittest.mock import patch

import typer

from hexastack.adapters.cli.scaffolding.commands.registration import (
    add_scaffold_commands,
)


def test_add_scaffold_commands_mounts_new_and_init():
    """Verify add_scaffold_commands mounts new app and registers init command."""
    app = typer.Typer()
    mock_new_app = typer.Typer()

    with (
        patch(
            "hexastack.adapters.cli.scaffolding.commands.registration.create_new_app",
            return_value=mock_new_app,
        ) as mock_create_new,
        patch(
            "hexastack.adapters.cli.scaffolding.commands.registration.add_init_command"
        ) as mock_add_init,
    ):
        add_scaffold_commands(app)

        called_create = mock_create_new.called
        assert called_create is True

        called_init = mock_add_init.called
        assert called_init is True
        mock_add_init.assert_called_once_with(app)
