"""CLI command definitions for demo showcase and diagnostics.

Notes/Architectural Intent:
    Provides subcommands for inspecting registries, running diagnostic queries,
    and launching interactive developer servers.
"""

from __future__ import annotations

import importlib.util

import typer

from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "add_ui_commands",
]


def add_ui_commands(app: typer.Typer) -> None:
    """Register 'ui' command to launch the interactive DevTools web dashboard."""

    @app.command(
        name="ui",
        help="Launch the Hexastack DevTools interactive web UI (requires hexastack[ui]).",
    )
    def ui_command(
        host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host."),
        port: int = typer.Option(8000, "--port", "-p", help="Bind port."),
        reload: bool = typer.Option(
            False, "--reload/--no-reload", help="Enable auto-reloading."
        ),
    ) -> None:
        if importlib.util.find_spec("nicegui") is None:
            raise MissingDependencyError(
                "NiceGUI is required to launch the interactive UI. "
                "Install via 'pip install hexastack[ui]' or 'pip install hexastack-fastapi[ui]'."
            )

        if importlib.util.find_spec("uvicorn") is None:
            raise MissingDependencyError(
                "uvicorn is required to run the web server. "
                "Install via 'pip install hexastack[web]' or 'pip install uvicorn[standard]'."
            )

        import uvicorn

        from hexastack.adapters.fastapi import create_demo_app

        typer.echo(f"Starting Hexastack DevTools at http://{host}:{port}/_devtools ...")
        demo_app = create_demo_app()
        uvicorn.run(demo_app, host=host, port=port, reload=reload)
