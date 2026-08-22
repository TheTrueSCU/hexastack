"""CLI command definitions for demo showcase and diagnostics.

Notes/Architectural Intent:
    Provides subcommands for inspecting registries, running diagnostic queries,
    and launching interactive developer servers.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
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
    "add_dev_command",
    "add_fastapi_commands",
    "add_graphql_commands",
    "add_grpc_commands",
    "add_load_command",
    "add_mcp_commands",
    "add_outbox_commands",
    "add_profile_command",
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

    @db_app.command(
        name="check",
        help="Verify there is no unapplied schema drift or missing migrations (Alembic check).",
    )
    def db_check(
        directory: str = typer.Option(
            "migrations", "--dir", help="Migrations directory."
        ),
        url: str | None = typer.Option(
            None, "--url", help="Database URL (overrides DATABASE_URL env var)."
        ),
    ) -> None:
        _require_migrations()
        from hexastack_db.infra.migrations import run_check

        try:
            run_check(_get_config(directory, url))
            typer.echo("✅ Database schema and migration revisions are fully in sync.")
        except Exception as e:
            typer.echo(f"❌ Schema drift detected: {e}")
            raise typer.Exit(code=1) from e

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


def _exec_grpc_serve(host: str, port: int) -> None:
    import grpc

    import hexastack.application.diagnostics
    from hexastack_core.infra.bootstrap import bootstrap
    from hexastack_grpc.adapters.server import run_grpc_server

    runtime = bootstrap(packages_to_scan=[hexastack.application.diagnostics])
    server = runtime.container.resolve(grpc.Server)
    typer.echo(f"Starting gRPC server on {host}:{port}...")
    run_grpc_server(server, block=True)


def _exec_grpc_compile(out_dir: str, proto_file: list[str] | None) -> None:
    from pathlib import Path

    from hexastack_grpc.infra.compiler import ProtoCompiler
    from hexastack_grpc.infra.registries.proto import get_proto_registry

    registry = get_proto_registry()
    entries = registry.entries

    if proto_file:
        generated = ProtoCompiler.compile_files(
            proto_files=proto_file,
            output_dir=Path(out_dir),
        )
    elif entries:
        generated = ProtoCompiler.compile_metadata(
            entries=entries,
            output_dir=Path(out_dir),
        )
    else:
        default_proto_dir = Path("protos")
        if default_proto_dir.exists():
            found_files = list(default_proto_dir.glob("**/*.proto"))
            if found_files:
                generated = ProtoCompiler.compile_files(
                    proto_files=found_files,
                    include_dirs=[default_proto_dir],
                    output_dir=Path(out_dir),
                )
            else:
                typer.echo(
                    "⚠️  No @proto_schema annotations, @proto_file decorators, or .proto files found."
                )
                return
        else:
            typer.echo(
                "⚠️  No @proto_schema annotations, @proto_file decorators, or .proto files found."
            )
            return

    typer.echo(
        f"✨ Successfully compiled {len(generated)} protobuf stubs into '{out_dir}':"
    )
    for g in generated:
        typer.echo(f"   • {g.name}")


def _exec_grpc_list() -> None:
    from hexastack_grpc.infra.decorators import get_grpc_registry
    from hexastack_grpc.infra.registries.proto import get_proto_registry

    proto_reg = get_proto_registry()
    grpc_reg = get_grpc_registry()

    typer.echo(
        "🔍 [bold cyan]Registered gRPC Services & Protobuf Schemas[/bold cyan]\n"
    )

    if not proto_reg.entries and not grpc_reg._services:
        typer.echo("   (No gRPC services or protobuf schemas registered)")
        return

    if proto_reg.entries:
        typer.echo("📜 [bold]Protobuf Schemas & Models:[/bold]")
        for entry in proto_reg.entries:
            src_type = (
                "inline @proto_schema" if entry.schema else f"file: {entry.file_path}"
            )
            rpc_info = (
                f" -> {entry.service_name}/{entry.rpc_name}"
                if entry.service_name
                else ""
            )
            typer.echo(
                f"   • [green]{entry.message_name}[/green] ({src_type}){rpc_info}"
            )
        typer.echo("")

    if grpc_reg._services:
        typer.echo("⚡ [bold]gRPC Servicers:[/bold]")
        for svc in grpc_reg._services:
            servicer_name = getattr(svc.servicer, "__name__", str(svc.servicer))
            names = ", ".join(svc.service_names) if svc.service_names else "default"
            typer.echo(f"   • [yellow]{servicer_name}[/yellow] (Services: {names})")


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

    @grpc_app.command(name="serve", help="Launch the gRPC server daemon.")
    def grpc_serve(
        host: str = typer.Option("0.0.0.0", "--host", "-h", help="Bind host."),
        port: int = typer.Option(50051, "--port", "-p", help="Bind port."),
    ) -> None:
        _exec_grpc_serve(host, port)

    @grpc_app.command(
        name="compile",
        help="Compile discovered @proto_schema inline strings and @proto_file definitions into Python stubs.",
    )
    def grpc_compile(
        out_dir: str = typer.Option(
            "src/generated/grpc",
            "--out-dir",
            "-o",
            help="Target output directory for generated protobuf stubs.",
        ),
        proto_file: list[str] | None = typer.Option(
            None,
            "--file",
            "-f",
            help="Optional explicit .proto file path(s) to compile.",
        ),
    ) -> None:
        _exec_grpc_compile(out_dir, proto_file)

    @grpc_app.command(
        name="list",
        help="Inspect and list registered gRPC services, RPC methods, and protobuf schemas.",
    )
    def grpc_list() -> None:
        _exec_grpc_list()


def _exec_mcp_config(
    client: str, server_name: str, command_override: str | None
) -> None:
    import json

    cmd = command_override or "uv"
    args = ["run", "hexastack", "mcp", "run"] if command_override is None else []
    client_key = client.lower().strip()

    if client_key in ("antigravity", "gemini", "agy"):
        config = {
            "mcpServers": {
                server_name: {
                    "command": cmd,
                    "args": args,
                    "env": {
                        "HEXASTACK_AI__PROVIDER": "gemini",
                        "PYTHONUNBUFFERED": "1",
                    },
                }
            }
        }
    elif client_key == "claude":
        config = {
            "mcpServers": {
                server_name: {
                    "command": cmd,
                    "args": args,
                    "env": {
                        "PYTHONUNBUFFERED": "1",
                    },
                }
            }
        }
    else:
        config = {
            "mcpServers": {
                server_name: {
                    "command": cmd,
                    "args": args,
                }
            }
        }

    typer.echo(json.dumps(config, indent=2))


def _exec_mcp_list() -> None:
    from hexastack_mcp.infra.decorators import get_mcp_registry

    registry = get_mcp_registry()
    typer.echo("🤖 [bold cyan]Model Context Protocol (MCP) Capabilities[/bold cyan]\n")

    typer.echo(f"🔧 [bold]Registered Tools ({len(registry.tools)}):[/bold]")
    if not registry.tools:
        typer.echo("   (No tools registered)")
    else:
        for t in registry.tools:
            desc = f" - {t.description}" if t.description else ""
            typer.echo(f"   • [green]{t.name}[/green] ({t.kind}){desc}")
    typer.echo("")

    typer.echo(f"📝 [bold]Prompts ({len(registry.prompts)}):[/bold]")
    if not registry.prompts:
        typer.echo("   (No prompt templates registered)")
    else:
        for p in registry.prompts:
            typer.echo(f"   • [yellow]{p.name}[/yellow]: {p.description}")
    typer.echo("")

    typer.echo(f"📦 [bold]Resources ({len(registry.resources)}):[/bold]")
    if not registry.resources:
        typer.echo("   (No resources registered)")
    else:
        for r in registry.resources:
            typer.echo(f"   • [magenta]{r.name}[/magenta] ({r.uri})")


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
        help="Launch the MCP server in stdio mode (for Claude, Cursor, Gemini, Antigravity).",
    )
    def mcp_run() -> None:
        from mcp.server.fastmcp import FastMCP as McpServer

        import hexastack.application.diagnostics
        from hexastack_core.infra.bootstrap import bootstrap
        from hexastack_mcp.adapters.stdio import run_stdio_server

        runtime = bootstrap(packages_to_scan=[hexastack.application.diagnostics])
        server = runtime.container.resolve(McpServer)
        run_stdio_server(server)

    @mcp_app.command(
        name="config",
        help="Generate MCP JSON configuration for Gemini / Antigravity, Claude Desktop, or Cursor.",
    )
    def mcp_config(
        client: str = typer.Option(
            "antigravity",
            "--client",
            "-c",
            help="Target client: 'antigravity', 'gemini', 'claude', 'cursor'.",
        ),
        server_name: str = typer.Option(
            "hexastack",
            "--name",
            "-n",
            help="Server name in the MCP client config.",
        ),
        command_override: str | None = typer.Option(
            None,
            "--command",
            help="Custom executable command (defaults to 'uv run hexastack mcp run').",
        ),
    ) -> None:
        _exec_mcp_config(client, server_name, command_override)

    @mcp_app.command(
        name="list",
        help="Inspect and list registered MCP tools, prompt templates, and resources.",
    )
    def mcp_list() -> None:
        _exec_mcp_list()


def add_outbox_commands(app: typer.Typer) -> None:
    """Register 'outbox' subcommand group for outbox relay daemon management."""
    if importlib.util.find_spec("hexastack_events") is None:
        return

    outbox_app = typer.Typer(
        name="outbox",
        help="Transactional Outbox background relay daemon (requires hexastack[events]).",
        no_args_is_help=True,
    )
    app.add_typer(outbox_app, name="outbox")

    @outbox_app.command(
        name="relay",
        help="Run the outbox relay background worker to drain and publish pending events.",
    )
    def outbox_relay(
        poll_interval: float = typer.Option(
            1.0,
            "--interval",
            "-i",
            help="Polling interval in seconds between sweeps.",
        ),
        batch_size: int = typer.Option(
            50,
            "--batch-size",
            "-b",
            help="Maximum number of outbox events to drain per sweep.",
        ),
        once: bool = typer.Option(
            False,
            "--once",
            help="Drain pending events once and exit immediately.",
        ),
    ) -> None:
        import asyncio

        from hexastack_cqrs.adapters.buses.event.synchronous import SynchronousEventBus
        from hexastack_events.adapters.outbox.asyncio import AsyncioOutboxRelay
        from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage

        storage = InMemoryOutboxStorage()
        bus = SynchronousEventBus()
        relay = AsyncioOutboxRelay(
            storage=storage,
            bus=bus,
            poll_interval_seconds=poll_interval,
            batch_size=batch_size,
        )

        if once:
            count = relay.publish_pending_batch(limit=batch_size)
            typer.echo(f"✨ Drained and published {count} pending outbox events.")
            return

        typer.echo(
            f"🚀 Starting Outbox Relay Daemon (polling every {poll_interval}s, batch size {batch_size})..."
        )
        typer.echo("   Press Ctrl+C to stop.")

        async def _run() -> None:
            relay.start()
            try:
                while True:
                    await asyncio.sleep(1.0)
            except (asyncio.CancelledError, KeyboardInterrupt):
                relay.stop()
                typer.echo("\n🛑 Stopped Outbox Relay Daemon.")

        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            typer.echo("\n🛑 Stopped Outbox Relay Daemon.")


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


def _start_fastapi_server(host: str, port: int) -> None:
    import uvicorn

    from hexastack.adapters.fastapi import create_demo_app

    app = create_demo_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


def _start_grpc_server(host: str, port: int) -> None:
    import grpc

    import hexastack.application.diagnostics
    from hexastack_core.infra.bootstrap import bootstrap
    from hexastack_grpc.adapters.server import run_grpc_server

    runtime = bootstrap(packages_to_scan=[hexastack.application.diagnostics])
    server = runtime.container.resolve(grpc.Server)
    run_grpc_server(server, block=True)


def _start_outbox_relay(interval: float, batch_size: int) -> None:
    import asyncio

    from hexastack_cqrs.adapters.buses.event.synchronous import SynchronousEventBus
    from hexastack_events.adapters.outbox.asyncio import AsyncioOutboxRelay
    from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage

    storage = InMemoryOutboxStorage()
    bus = SynchronousEventBus()
    relay = AsyncioOutboxRelay(
        storage=storage,
        bus=bus,
        poll_interval_seconds=interval,
        batch_size=batch_size,
    )

    async def _run() -> None:
        relay.start()
        try:
            while True:
                await asyncio.sleep(1.0)
        except (asyncio.CancelledError, KeyboardInterrupt):
            relay.stop()

    import contextlib

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run())


def add_dev_command(app: typer.Typer) -> None:
    """Register 'dev' command to concurrently launch multi-transport development servers."""

    @app.command(
        name="dev",
        help="Launch concurrent multi-transport dev environment (REST on 8000, gRPC on 50051, Outbox relay).",
    )
    def dev_command(
        host: str = typer.Option(
            "127.0.0.1", "--host", "-h", help="Bind host address."
        ),
        http_port: int = typer.Option(8000, "--port", "-p", help="REST HTTP port."),
        grpc_port: int = typer.Option(50051, "--grpc-port", help="gRPC port."),
        with_grpc: bool = typer.Option(
            True, "--grpc/--no-grpc", help="Launch gRPC server."
        ),
        with_outbox: bool = typer.Option(
            True, "--outbox/--no-outbox", help="Launch Outbox relay daemon."
        ),
    ) -> None:
        import multiprocessing
        import time

        typer.echo(
            "🚀 [bold cyan]Hexastack Multi-Transport Development Environment[/bold cyan]\n"
        )
        typer.echo(
            f"   • 🌐 REST API:    http://{host}:{http_port} (Swagger UI at http://{host}:{http_port}/_devtools)"
        )

        processes: list[multiprocessing.Process] = []

        # 1. FastAPI REST
        p_http = multiprocessing.Process(
            target=_start_fastapi_server,
            args=(host, http_port),
            name="REST-Server",
        )
        processes.append(p_http)

        # 2. gRPC (if available and enabled)
        if with_grpc and importlib.util.find_spec("hexastack_grpc") is not None:
            typer.echo(
                f"   • ⚡ gRPC Daemon:  {host}:{grpc_port} (Server reflection active)"
            )
            p_grpc = multiprocessing.Process(
                target=_start_grpc_server,
                args=(host, grpc_port),
                name="gRPC-Server",
            )
            processes.append(p_grpc)

        # 3. Outbox Relay (if available and enabled)
        if with_outbox and importlib.util.find_spec("hexastack_events") is not None:
            typer.echo("   • 📬 Outbox Relay: Active background polling worker")
            p_outbox = multiprocessing.Process(
                target=_start_outbox_relay,
                args=(1.0, 50),
                name="Outbox-Relay",
            )
            processes.append(p_outbox)

        typer.echo(
            "\n✨ All transports launched. Press Ctrl+C to terminate all servers.\n"
        )

        for p in processes:
            p.start()

        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            typer.echo("\n🛑 Shutting down development servers...")
            for p in processes:
                p.terminate()
                p.join(timeout=2.0)
            typer.echo("✅ All services stopped.")


def add_profile_command(app: typer.Typer) -> None:
    """Register 'profile' CLI command to capture CPU or Memory flamegraphs with py-spy and memray."""
    profile_app = typer.Typer(
        name="profile",
        help="Profile CPU performance or memory allocations with interactive flamegraphs.",
        no_args_is_help=True,
    )
    app.add_typer(profile_app, name="profile")

    @profile_app.command(
        name="cpu",
        help="Capture CPU flamegraph with py-spy (attach to PID or wrap server command).",
    )
    def profile_cpu(
        pid: int | None = typer.Option(
            None, "--pid", "-p", help="Target process ID to attach to."
        ),
        duration: int = typer.Option(
            15, "--duration", "-d", help="Profiling duration in seconds."
        ),
        output: str = typer.Option(
            "cpu_flamegraph.svg",
            "--output",
            "-o",
            help="Output SVG flamegraph filepath.",
        ),
        rate: int = typer.Option(100, "--rate", "-r", help="Samples per second."),
    ) -> None:
        if importlib.util.find_spec("py_spy") is None:
            raise MissingDependencyError(
                "py-spy is required for CPU profiling. Install with 'uv add --dev py-spy'."
            )
        import subprocess

        if pid is None:
            typer.echo(
                "⚠️ No PID provided. Launch your service with 'hexastack dev', find the PID, and pass '--pid <PID>'."
            )
            raise typer.Exit(code=1)

        typer.echo(
            f"🔥 Profiling CPU on PID {pid} for {duration}s @ {rate}Hz -> {output}..."
        )
        cmd = [
            "py-spy",
            "record",
            "-p",
            str(pid),
            "-d",
            str(duration),
            "-r",
            str(rate),
            "-o",
            output,
        ]
        res = subprocess.run(cmd, check=False)
        if res.returncode == 0:
            typer.echo(f"✅ CPU flamegraph saved to: {Path(output).resolve()}")
        else:
            typer.echo(
                "❌ py-spy failed. You may need 'sudo' on Linux to attach to processes."
            )

    @profile_app.command(
        name="memory",
        help="Generate memory allocation flamegraph using memray.",
    )
    def profile_memory(
        bin_file: str = typer.Option(
            "mem_profile.bin",
            "--bin",
            "-b",
            help="Intermediate binary memory capture file.",
        ),
        output: str = typer.Option(
            "mem_flamegraph.html",
            "--output",
            "-o",
            help="Output HTML flamegraph filepath.",
        ),
    ) -> None:
        if importlib.util.find_spec("memray") is None:
            raise MissingDependencyError(
                "memray is required for Memory profiling. Install with 'uv add --dev memray'."
            )
        import subprocess

        if not Path(bin_file).exists():
            typer.echo(
                f"ℹ️ Target capture file '{bin_file}' not found.\n"
                f"Run your application under memray first:\n"
                f"  uv run memray run -o {bin_file} -m hexastack dev\n"
            )
            raise typer.Exit(code=1)

        typer.echo(f"🧠 Rendering memory flamegraph from {bin_file} -> {output}...")
        cmd = ["memray", "flamegraph", bin_file, "-o", output]
        res = subprocess.run(cmd, check=False)
        if res.returncode == 0:
            typer.echo(f"✅ Memory flamegraph saved to: {Path(output).resolve()}")
        else:
            typer.echo("❌ memray flamegraph rendering failed.")


def add_load_command(app: typer.Typer) -> None:
    """Register 'load' CLI command to execute stress tests via Locust."""

    @app.command(
        name="load",
        help="Execute concurrent load/stress testing scenario using Locust.",
    )
    def load_command(
        host: str = typer.Option(
            "http://127.0.0.1:8000", "--host", "-h", help="Target service host URL."
        ),
        users: int = typer.Option(
            50, "--users", "-u", help="Peak number of concurrent virtual users."
        ),
        spawn_rate: int = typer.Option(
            10, "--spawn-rate", "-r", help="Rate to spawn users per second."
        ),
        run_time: str = typer.Option(
            "15s", "--run-time", "-t", help="Total benchmark run time (e.g. 15s, 1m)."
        ),
        locustfile: str = typer.Option(
            "locustfile.py", "--locustfile", "-f", help="Locustfile scenario filepath."
        ),
        headless: bool = typer.Option(
            True, "--headless/--web", help="Run headlessly in CLI without Web UI."
        ),
    ) -> None:
        if importlib.util.find_spec("locust") is None:
            raise MissingDependencyError(
                "locust is required for load testing. Install with 'uv add --dev locust'."
            )
        import subprocess

        # If default locustfile doesn't exist, create a default in-memory benchmark scenario
        target_locust_path = Path(locustfile)
        if not target_locust_path.exists() and locustfile == "locustfile.py":
            default_content = '''"""Automated default Locust scenario for Hexastack microservices."""

from locust import HttpUser, between, task


class HexastackUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @task(3)
    def get_health(self):
        self.client.get("/health")

    @task(2)
    def get_info(self):
        self.client.get("/info")
'''
            target_locust_path.write_text(default_content, encoding="utf-8")
            typer.echo(f"📝 Generated default '{locustfile}' scenario.")

        typer.echo(
            f"🦗 Launching Locust: {users} users @ {spawn_rate}/s for {run_time} against {host}..."
        )

        cmd = [
            "locust",
            "-f",
            locustfile,
            "--host",
            host,
        ]
        if headless:
            cmd.extend(
                [
                    "--headless",
                    "-u",
                    str(users),
                    "-r",
                    str(spawn_rate),
                    "--run-time",
                    run_time,
                    "--exit-code-on-error",
                    "1",
                ]
            )

        res = subprocess.run(cmd, check=False)
        if res.returncode == 0:
            typer.echo("✅ Load benchmark completed successfully.")
        else:
            typer.echo("⚠️ Load benchmark exited with errors.")
            raise typer.Exit(code=res.returncode)
