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
    "add_serve_command",
]


def add_serve_command(app: typer.Typer) -> None:
    """Register 'serve' command to launch the local FastAPI dev server using Uvicorn.

    Args:
        app: Target Typer application instance.
    """

    @app.command(
        name="serve",
        help="Launch the Hexastack local development server (requires hexastack[web]).",
    )
    def serve(
        host: str = typer.Option(
            "127.0.0.1", "--host", "-h", help="Bind host address."
        ),
        port: int = typer.Option(8000, "--port", "-p", help="Bind port number."),
        reload: bool = typer.Option(
            True, "--reload/--no-reload", help="Enable live reloading."
        ),
    ) -> None:
        if importlib.util.find_spec("uvicorn") is None:
            raise MissingDependencyError(
                "uvicorn is required to run the local server. "
                "Install via 'pip install hexastack[web]' or 'pip install uvicorn[standard]'."
            )

        if importlib.util.find_spec("fastapi") is None:
            raise MissingDependencyError(
                "fastapi is required to run the local server. "
                "Install via 'pip install hexastack[fastapi]'."
            )

        import uvicorn

        from hexastack.adapters.fastapi import create_demo_app

        demo_app = create_demo_app()
        uvicorn.run(demo_app, host=host, port=port, reload=reload)
