import importlib.util

import typer
from hexastack_cli.infra.decorators import (
    cli_command,
    cli_group,
    cli_query,
)
from hexastack_core.domain.exceptions import MissingDependencyError

from hexastack.domain.diagnostics import (
    GetSystemInfoQuery,
    InspectRegistryQuery,
    PingDemoCommand,
)


@cli_group("inspect", help="Introspect registered CQRS handlers, routes, and config")
class InspectGroupDocs:
    pass


@cli_group("demo", help="Interactive demonstration commands")
class DemoGroupDocs:
    pass


# Decorate diagnostics domain models with CLI exposure metadata
cli_query(
    "info",
    aliases=["doctor", "status"],
    help="Display installed Hexastack packages and optional dependency statuses.",
)(GetSystemInfoQuery)

cli_query(
    "registry",
    group="inspect",
    aliases=["handlers"],
    help="Display registered CQRS commands, queries, and configurations.",
)(InspectRegistryQuery)

cli_command(
    "ping",
    group="demo",
    aliases=["/ping"],
    help="Send a test ping command through the CQRS execution pipeline.",
)(PingDemoCommand)


def add_serve_command(app: typer.Typer) -> None:
    """Register 'serve' command to launch the local FastAPI dev server using Uvicorn.

    Args:
        app: Target Typer application instance.

    Returns:
        None.

    Raises:
        None.
    """

    @app.command(
        name="serve",
        help="Launch the Hexastack local development server (requires hexastack[web]).",
    )
    def serve(
        host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address."),
        port: int = typer.Option(8000, "--port", "-p", help="Bind port number."),
        reload: bool = typer.Option(True, "--reload/--no-reload", help="Enable live reloading."),
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


__all__ = [
    "DemoGroupDocs",
    "InspectGroupDocs",
    "add_serve_command",
]
