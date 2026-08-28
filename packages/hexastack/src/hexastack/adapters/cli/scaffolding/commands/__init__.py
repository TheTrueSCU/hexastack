"""CLI scaffolding commands module initializer."""

from __future__ import annotations

import typer

from hexastack.adapters.cli.scaffolding.commands.init import add_init_command
from hexastack.adapters.cli.scaffolding.commands.new import create_new_app

__all__ = [
    "add_scaffold_commands",
]


def add_scaffold_commands(app: typer.Typer) -> None:
    """Register 'new' and 'init' project scaffolding commands with Typer application instance.

    Args:
        app: Target Typer application instance.
    """
    new_app = create_new_app()
    app.add_typer(new_app, name="new")
    add_init_command(app)
