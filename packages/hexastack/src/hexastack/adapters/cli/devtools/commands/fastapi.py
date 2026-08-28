"""CLI command definitions for demo showcase and diagnostics.

Notes/Architectural Intent:
    Provides subcommands for inspecting registries, running diagnostic queries,
    and launching interactive developer servers.
"""

from __future__ import annotations

import importlib.util

import typer

__all__ = [
    "add_fastapi_commands",
]


def add_fastapi_commands(app: typer.Typer) -> None:
    """Register 'fastapi' subcommand group for REST route introspection."""
    if importlib.util.find_spec("hexastack_fastapi") is None:
        return

    fastapi_app = typer.Typer(
        name="fastapi",
        help="FastAPI REST routes and OpenAPI introspection (requires hexastack[fastapi]).",
        no_args_is_help=True,
    )
    app.add_typer(fastapi_app, name="fastapi")

    @fastapi_app.command(
        name="routes",
        help="List all registered REST endpoints and CQRS bindings.",
    )
    def fastapi_routes() -> None:
        from hexastack.adapters.fastapi import create_demo_app

        demo_app = create_demo_app()
        typer.echo("🌐 [bold cyan]Registered FastAPI REST Endpoints[/bold cyan]\n")

        for route in demo_app.routes:
            methods = getattr(route, "methods", None)
            path = getattr(route, "path", None)
            name = getattr(route, "name", None)
            if methods and path:
                methods_str = ", ".join(methods - {"HEAD", "OPTIONS"})
                if methods_str:
                    typer.echo(
                        f"   • [bold green]{methods_str:<6}[/bold green] [yellow]{path}[/yellow] ({name})"
                    )
