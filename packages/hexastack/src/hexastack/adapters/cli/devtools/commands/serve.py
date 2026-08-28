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
