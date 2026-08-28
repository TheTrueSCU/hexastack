"""CLI command definitions for demo showcase and diagnostics.

Notes/Architectural Intent:
    Provides subcommands for inspecting registries, running diagnostic queries,
    and launching interactive developer servers.
"""

from __future__ import annotations

import importlib.util

import typer

__all__ = [
    "add_graphql_commands",
]


def add_graphql_commands(app: typer.Typer) -> None:
    """Register 'graphql' subcommand group for schema introspection."""
    if importlib.util.find_spec("hexastack_graphql") is None:
        return

    graphql_app = typer.Typer(
        name="graphql",
        help="GraphQL schema SDL and introspection (requires hexastack[graphql]).",
        no_args_is_help=True,
    )
    app.add_typer(graphql_app, name="graphql")

    @graphql_app.command(
        name="schema",
        help="Export or print the complete GraphQL Schema Definition (SDL).",
    )
    def graphql_schema() -> None:
        import strawberry

        import hexastack.application.diagnostics
        from hexastack_core.infra.bootstrap import bootstrap

        runtime = bootstrap(packages_to_scan=[hexastack.application.diagnostics])
        try:
            schema = runtime.container.resolve(strawberry.Schema)
            typer.echo(schema.as_str())
        except Exception:
            typer.echo(
                "⚠️  No Strawberry GraphQL Schema currently registered in container."
            )
