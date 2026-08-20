"""Typer CLI driving adapters exposing CQRS commands."""

import sys

from hexastack_cli.infra.decorators import cli_command, cli_query

from todo_app.domain.commands import (
    CompleteTodoCommand,
    CreateTodoCommand,
    DeleteTodoCommand,
    ListTodosQuery,
)

# Register CLI commands and queries
cli_command(
    "create",
    help="Create a new To-Do task.",
)(CreateTodoCommand)

cli_command(
    "complete",
    help="Mark a To-Do task as completed.",
)(CompleteTodoCommand)

cli_command(
    "delete",
    help="Delete a To-Do task.",
)(DeleteTodoCommand)

cli_query(
    "list",
    help="List all To-Do tasks.",
)(ListTodosQuery)


def main() -> None:
    """CLI script entrypoint."""
    from todo_app.infra.bootstrap import create_app

    app = create_app()
    cli_app = app.get("cli_app")
    if cli_app is not None:
        cli_app()
    else:
        sys.stderr.write("CLI application failed to bootstrap.\n")
        sys.exit(1)
