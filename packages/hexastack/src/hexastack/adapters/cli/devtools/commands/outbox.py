"""CLI command definitions for demo showcase and diagnostics.

Notes/Architectural Intent:
    Provides subcommands for inspecting registries, running diagnostic queries,
    and launching interactive developer servers.
"""

from __future__ import annotations

import importlib.util

import typer

__all__ = [
    "add_outbox_commands",
]


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
