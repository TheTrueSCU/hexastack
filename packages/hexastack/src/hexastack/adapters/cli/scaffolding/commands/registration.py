"""CLI command registration logic for project scaffolding.

Notes/Architectural Intent:
    Decouples Typer command and sub-application mounting logic from package
    initializers (`__init__.py`), ensuring clean, side-effect-free imports
    and adherence to hexagonal architecture boundaries.
"""

from __future__ import annotations

import typer

from hexastack.adapters.cli.scaffolding.commands.init import add_init_command
from hexastack.adapters.cli.scaffolding.commands.new import create_new_app

__all__ = [
    "add_scaffold_commands",
]


def add_scaffold_commands(app: typer.Typer) -> None:
    """Register 'new' and 'init' project scaffolding commands with a Typer application.

    Args:
        app: Target Typer application instance to mount scaffolding commands onto.

    Notes/Architectural Intent:
        Mounts the nested `new` Typer sub-application and registers the top-level
        `init` wizard command directly on the provided CLI application root.
    """
    new_app = create_new_app()
    app.add_typer(new_app, name="new")
    add_init_command(app)

    scaffold_app = typer.Typer(
        name="scaffold",
        help="Project lifecycle and scaffolding tools (new, init).",
        no_args_is_help=True,
    )
    scaffold_app.add_typer(create_new_app(), name="new")
    add_init_command(scaffold_app)
    app.add_typer(scaffold_app, name="scaffold")
