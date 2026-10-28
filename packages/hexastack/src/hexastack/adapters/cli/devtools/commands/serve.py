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
        engine: str = typer.Option(
            "uvicorn",
            "--engine",
            "-e",
            help="ASGI server engine to execute ('uvicorn' or 'granian').",
        ),
        workers: int | None = typer.Option(
            None,
            "--workers",
            "-w",
            help="Number of worker processes (defaults to 1 or CPU core count).",
        ),
        ziti_identity: str | None = typer.Option(
            None,
            "--ziti-identity",
            "-z",
            help="Path to enrolled OpenZiti identity JSON to host as zero-trust dark microservice.",
        ),
        ziti_service: str | None = typer.Option(
            None,
            "--ziti-service",
            help="OpenZiti service name to bind on overlay fabric (defaults to 'hexastack-demo').",
        ),
    ) -> None:
        if (
            importlib.util.find_spec("fastapi") is None
            or importlib.util.find_spec("hexastack_fastapi") is None
        ):
            raise MissingDependencyError(
                "fastapi and hexastack-fastapi are required to run the local server. "
                "Install via 'pip install hexastack[fastapi]'."
            )

        if ziti_identity is not None:
            if engine.lower() != "uvicorn":
                raise typer.BadParameter(
                    f"OpenZiti overlay requires 'uvicorn' engine (got '{engine}')."
                )
            from rich.console import Console

            from hexastack_fastapi.adapters.openziti import (
                OpenZitiASGIAdapter,
                OpenZitiConfig,
            )

            svc_name = ziti_service or "hexastack-demo"
            console = Console()
            console.print(
                f"[bold cyan]Zero-Trust Dark Service:[/] Hosting '{svc_name}' over OpenZiti overlay (0 open ports on host)."
            )
            ziti_config = OpenZitiConfig(
                identity_path=ziti_identity,
                service_name=svc_name,
                bind_host=host,
                bind_port=port,
            )
            adapter = OpenZitiASGIAdapter(ziti_config)
            if reload:
                adapter.run_uvicorn(
                    "hexastack.adapters.fastapi:create_demo_app",
                    factory=True,
                    reload=True,
                )
            else:
                from hexastack.adapters.fastapi import create_demo_app

                demo_app = create_demo_app()
                adapter.run_uvicorn(demo_app, reload=False)
            return

        from hexastack_fastapi.adapters.server import run_server

        run_server(
            "hexastack.adapters.fastapi:create_demo_app",
            engine=engine,
            host=host,
            port=port,
            reload=reload,
            workers=workers,
            factory=True,
        )
