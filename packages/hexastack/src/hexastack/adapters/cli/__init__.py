"""CLI adapters for Hexastack umbrella package.

Sub-packages:
    scaffolding: Project creation and initialization commands (`new`, `init`).
    demo: Showcase, diagnostics, server, and UI commands (`demo`, `ui`, `serve`, `db`, `grpc`, `mcp`).
"""

from hexastack.adapters.cli.demo.commands import (
    DemoGroupDocs,
    InspectGroupDocs,
    add_db_commands,
    add_fastapi_commands,
    add_graphql_commands,
    add_grpc_commands,
    add_mcp_commands,
    add_outbox_commands,
    add_serve_command,
    add_ui_commands,
)
from hexastack.adapters.cli.scaffolding.commands import add_scaffold_commands

__all__ = [
    "add_db_commands",
    "add_fastapi_commands",
    "add_graphql_commands",
    "add_grpc_commands",
    "add_mcp_commands",
    "add_outbox_commands",
    "add_scaffold_commands",
    "add_serve_command",
    "add_ui_commands",
    "DemoGroupDocs",
    "InspectGroupDocs",
]
