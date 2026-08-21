"""Demo showcase and diagnostic CLI commands."""

from hexastack.adapters.cli.demo.commands import (
    DemoGroupDocs,
    InspectGroupDocs,
    add_db_commands,
    add_grpc_commands,
    add_mcp_commands,
    add_outbox_commands,
    add_serve_command,
    add_ui_commands,
)

__all__ = [
    "add_db_commands",
    "add_grpc_commands",
    "add_mcp_commands",
    "add_outbox_commands",
    "add_serve_command",
    "add_ui_commands",
    "DemoGroupDocs",
    "InspectGroupDocs",
]
