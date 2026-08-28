"""Unit tests for scaffolding commands root module."""

import typer

from hexastack.adapters.cli.scaffolding.commands import add_scaffold_commands


def test_scaffold_commands_registration():
    app = typer.Typer()
    add_scaffold_commands(app)
    assert app is not None
