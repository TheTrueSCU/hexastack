"""CLI dev server orchestration command."""

from __future__ import annotations

import importlib.util
import multiprocessing
import time

import typer

__all__ = [
    "add_dev_command",
]


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
