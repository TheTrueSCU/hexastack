"""CLI diagnostics and inspection command decorations."""

from __future__ import annotations

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

__all__ = [
    "DemoGroupDocs",
    "InspectGroupDocs",
]


@cli_group("demo", help="Interactive demonstration commands")
class DemoGroupDocs:
    """CLI group documentation container for demo commands."""


@cli_group("inspect", help="Introspect registered CQRS handlers, routes, and config")
class InspectGroupDocs:
    """CLI group documentation container for inspect commands."""


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
