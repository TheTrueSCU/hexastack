"""CLI devtools commands module aggregating all developer tools."""

from __future__ import annotations

from hexastack.adapters.cli.devtools.commands.db import add_db_commands
from hexastack.adapters.cli.devtools.commands.dev import add_dev_command
from hexastack.adapters.cli.devtools.commands.fastapi import add_fastapi_commands
from hexastack.adapters.cli.devtools.commands.graphql import add_graphql_commands
from hexastack.adapters.cli.devtools.commands.grpc import add_grpc_commands
from hexastack.adapters.cli.devtools.commands.inspect import (
    DemoGroupDocs,
    InspectGroupDocs,
)
from hexastack.adapters.cli.devtools.commands.mcp import add_mcp_commands
from hexastack.adapters.cli.devtools.commands.outbox import add_outbox_commands
from hexastack.adapters.cli.devtools.commands.profiling import (
    add_load_command,
    add_profile_command,
)
from hexastack.adapters.cli.devtools.commands.serve import add_serve_command
from hexastack.adapters.cli.devtools.commands.ui import add_ui_commands

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
