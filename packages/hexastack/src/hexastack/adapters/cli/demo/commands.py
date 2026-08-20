"""CLI command definitions for demo showcase and diagnostics.

Notes/Architectural Intent:
    Provides subcommands for inspecting registries, running diagnostic queries,
    and launching interactive developer servers.
"""

from __future__ import annotations

import importlib.util
import os
from typing import Any

import typer

from hexastack.domain.diagnostics import (
    GetSystemInfoQuery,
    InspectRegistryQuery,
    PingDemoCommand,
)
from hexastack_cli.infra.decorators import (
    cli_command,
    cli_group,
    cli_query,
)
from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "add_db_commands",
    "add_grpc_commands",
    "add_mcp_commands",
    "add_serve_command",
    "add_ui_commands",
    "DemoGroupDocs",
    "InspectGroupDocs",
]


@cli_group("demo", help="Interactive demonstration commands")
class DemoGroupDocs:
    """CLI group documentation container for demo commands."""

    pass


@cli_group("inspect", help="Introspect registered CQRS handlers, routes, and config")
class InspectGroupDocs:
    """CLI group documentation container for inspect commands."""

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


def add_db_commands(app: typer.Typer) -> None:
    """Register 'db' subcommand group with migration management commands."""
    if importlib.util.find_spec("hexastack_db") is None:
        return

    db_app = typer.Typer(
        name="db",
        help="Database migration management (requires hexastack[db,migrations]).",
        no_args_is_help=True,
    )
    app.add_typer(db_app, name="db")

    def _require_migrations() -> None:
        if importlib.util.find_spec("alembic") is None:
            raise MissingDependencyError(
                "alembic is required for migration commands. "
                "Install via 'pip install hexastack-db[migrations]'."
            )

    def _get_config(migrations_dir: str, url: str | None) -> Any:
        from hexastack_db.infra.migrations import get_alembic_config

        db_url = url or os.environ.get("DATABASE_URL", "sqlite:///hexastack.db")
        return get_alembic_config(
            migrations_dir=migrations_dir,
            db_url=db_url,
        )

    @db_app.command(name="init", help="Scaffold a new migrations directory.")
    def db_init(
        directory: str = typer.Argument(
            "migrations", help="Path to create the migrations directory."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import init_migrations

        init_migrations(directory)

    @db_app.command(
        name="migrate", help="Apply pending database migrations (upgrade to head)."
    )
    def db_migrate(
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        revision: str = typer.Option("head", "--revision", help="Target revision."),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_upgrade

        run_upgrade(_get_config(directory, url), revision=revision)

    @db_app.command(name="revision", help="Generate a new migration revision script.")
    def db_revision(
        message: str = typer.Argument(..., help="Short description of the migration."),
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        no_autogenerate: bool = typer.Option(
            False, "--no-autogenerate", help="Disable schema autogeneration."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_revision

        run_revision(
            _get_config(directory, url),
            message=message,
            autogenerate=not no_autogenerate,
        )

    @db_app.command(name="current", help="Show the current applied revision.")
    def db_current(
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_current

        run_current(_get_config(directory, url))

    @db_app.command(name="history", help="Show migration revision history.")
    def db_history(
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_history

        run_history(_get_config(directory, url))

    @db_app.command(
        name="stamp",
        help="Stamp the database at a revision without running migrations.",
    )
    def db_stamp(
        revision: str = typer.Argument(
            "head", help="Revision to stamp (default: head)."
        ),
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import stamp

        stamp(_get_config(directory, url), revision)


def add_grpc_commands(app: typer.Typer) -> None:
    """Register 'grpc' subcommand group for RPC services."""
    if importlib.util.find_spec("hexastack_grpc") is None:
        return

    grpc_app = typer.Typer(
        name="grpc",
        help="High-performance gRPC server management.",
        no_args_is_help=True,
    )
    app.add_typer(grpc_app, name="grpc")

    @grpc_app.command(
        name="serve",
        help="Launch the gRPC server daemon.",
    )
    def grpc_serve(
        host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host."),
        port: int = typer.Option(50051, "--port", "-p", help="Bind port."),
    ) -> None:
        import grpc

        import hexastack.application.diagnostics
        from hexastack_core.infra.bootstrap import bootstrap
        from hexastack_grpc.adapters.server import run_grpc_server

        runtime = bootstrap(packages_to_scan=[hexastack.application.diagnostics])
        server = runtime.container.resolve(grpc.Server)
        typer.echo(f"Starting gRPC server on {host}:{port}...")
        run_grpc_server(server, block=True)


def add_mcp_commands(app: typer.Typer) -> None:
    """Register 'mcp' subcommand group for AI agent integration."""
    if importlib.util.find_spec("hexastack_mcp") is None:
        return

    mcp_app = typer.Typer(
        name="mcp",
        help="Model Context Protocol (MCP) AI agent tools and server.",
        no_args_is_help=True,
    )
    app.add_typer(mcp_app, name="mcp")

    @mcp_app.command(
        name="run",
        help="Launch the MCP server in stdio mode (for Claude, Cursor, Antigravity).",
    )
    def mcp_run() -> None:
        from mcp.server.fastmcp import FastMCP as McpServer

        import hexastack.application.diagnostics
        from hexastack_core.infra.bootstrap import bootstrap
        from hexastack_mcp.adapters.stdio import run_stdio_server

        runtime = bootstrap(packages_to_scan=[hexastack.application.diagnostics])
        server = runtime.container.resolve(McpServer)
        run_stdio_server(server)


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
