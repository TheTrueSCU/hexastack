"""Adapters layer template renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack.application.scaffolding.generator import ScaffoldConfig


def render_driven_database(package_name: str) -> str:
    return f'''"""In-memory and persistent database adapters."""

from typing import Optional
from {package_name}.domain.models import Item
from {package_name}.ports.repositories import ItemRepositoryPort


class InMemoryItemRepository(ItemRepositoryPort):
    """In-memory repository adapter for local development and unit tests."""

    def __init__(self) -> None:
        self._storage: dict[str, Item] = {{}}

    def save(self, item: Item) -> None:
        self._storage[item.id] = item

    def get_by_id(self, item_id: str) -> Optional[Item]:
        return self._storage.get(item_id)
'''


def render_driving_cli(package_name: str) -> str:
    return f'''"""Typer CLI entrypoint and driving command adapters."""

import sys
import typer
from hexastack_cli.infra.decorators import cli_command
from {package_name}.domain.commands import CreateItemCommand

cli_command("create-item", help="Create a new Item in the system.")(CreateItemCommand)

def main() -> None:
    """CLI entrypoint."""
    from {package_name}.infra.bootstrap import create_app
    app = create_app()
    cli_app = app.get("cli_app")
    if cli_app is not None:
        cli_app()
    else:
        sys.stderr.write("CLI application failed to bootstrap.\n")
        sys.exit(1)
'''


def render_driving_http(package_name: str) -> str:
    return f'''"""FastAPI REST routing adapters."""

from hexastack_fastapi.infra.decorators import api_command
from {package_name}.domain.commands import CreateItemCommand

api_command("/items", method="POST", summary="Create a new Item")(CreateItemCommand)
'''


def render_driving_grpc(package_name: str) -> str:
    return f'''"""High-performance gRPC driving adapter with inline @proto_schema contract."""

from dataclasses import dataclass
from hexastack_grpc.infra.decorators import proto_schema
from {package_name}.domain.commands import CreateItemCommand


@proto_schema(
    schema="""
    syntax = "proto3";
    package {package_name}.v1;

    message CreateItemRequest {{
        string title = 1;
        string description = 2;
    }}

    message CreateItemResponse {{
        string id = 1;
        string title = 2;
    }}

    service ItemService {{
        rpc CreateItem (CreateItemRequest) returns (CreateItemResponse);
    }}
    """,
    message_name="CreateItemRequest",
    service_name="{package_name}.v1.ItemService",
    rpc_name="CreateItem",
)
@dataclass
class CreateItemRpcCommand(CreateItemCommand):
    """gRPC Inbound Command contract."""
'''


def render_buf_yaml() -> str:
    return """version: v2
modules:
  - path: protos
lint:
  use:
    - DEFAULT
breaking:
  use:
    - FILE
"""


def render_proto_file(package_name: str) -> str:
    return f"""syntax = "proto3";

package {package_name}.v1;

message CreateItemRequest {{
  string title = 1;
  string description = 2;
}}

message CreateItemResponse {{
  string id = 1;
  string title = 2;
}}

service ItemService {{
  rpc CreateItem(CreateItemRequest) returns (CreateItemResponse);
}}
"""


def render_driving_graphql(package_name: str) -> str:
    return f'''"""Strawberry GraphQL driving schema and query/mutation resolvers."""

import strawberry
from hexastack_cqrs.ports.buses import CommandBusPort
from {package_name}.domain.commands import CreateItemCommand


@strawberry.type
class ItemGqlType:
    id: str
    title: str


@strawberry.type
class Query:
    @strawberry.field
    def health(self) -> str:
        return "OK"


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_item(self, info: strawberry.Info, title: str, description: str = "") -> ItemGqlType:
        bus = info.context["command_bus"]
        cmd = CreateItemCommand(title=title, description=description)
        result = bus.dispatch(cmd)
        return ItemGqlType(id=result.id, title=result.title)


schema = strawberry.Schema(query=Query, mutation=Mutation)
'''


def render_driving_mcp(package_name: str) -> str:
    return f'''"""Model Context Protocol (MCP) tool exposure for Gemini, Antigravity, and Claude."""

from hexastack_mcp.infra.decorators import mcp_tool
from {package_name}.domain.commands import CreateItemCommand

# Expose CreateItemCommand as an MCP tool for AI agents
mcp_tool(
    name="create_item",
    description="Create a new Item in the system with title and description",
    kind="command",
)(CreateItemCommand)
'''


def render_mcp_json(config: ScaffoldConfig) -> str:
    return f"""{{
  "mcpServers": {{
    "{config.name}": {{
      "command": "uv",
      "args": ["run", "{config.name}", "mcp", "run"],
      "env": {{
        "HEXASTACK_AI__PROVIDER": "gemini",
        "PYTHONUNBUFFERED": "1"
      }}
    }}
  }}
}}
"""
