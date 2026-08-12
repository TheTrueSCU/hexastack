import json
from dataclasses import dataclass

import pytest
from hexastack_core.domain.command import Command
from hexastack_core.domain.query import Query
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_cqrs.infra.decorators import command_handler, query_handler
from hexastack_mcp.infra.config import HexastackMcpConfig
from hexastack_mcp.infra.decorators import (
    get_mcp_registry,
    mcp_prompt,
    mcp_resource,
    mcp_tool,
)
from mcp.types import CallToolResult, TextContent


@pytest.fixture(autouse=True)
def clean_registry():
    reg = get_mcp_registry()
    reg.clear()
    yield
    reg.clear()


@dataclass(frozen=True)
class CalculateTaxCommand(Command):
    amount: float
    rate: float


@command_handler(CalculateTaxCommand)
class CalculateTaxHandler:
    def __call__(self, cmd: CalculateTaxCommand) -> dict[str, float]:
        return {"tax": cmd.amount * cmd.rate}


@dataclass(frozen=True)
class GetServerVersionQuery(Query):
    component: str


@query_handler(GetServerVersionQuery)
class GetServerVersionHandler:
    def __call__(self, qry: GetServerVersionQuery) -> str:
        return f"{qry.component}-v2.0"


@pytest.mark.anyio
async def test_mcp_server_registry_tools_execution():
    @mcp_tool(name="calc_tax", description="Calculate tax for an amount")
    class TaxCmd(CalculateTaxCommand):
        pass

    @mcp_tool(name="get_version", kind="query")
    class VersionQry(GetServerVersionQuery):
        pass

    @mcp_tool(name="echo_tool")
    def echo(msg: str) -> str:
        return f"ECHO: {msg}"

    @mcp_resource(uri="hexastack://status", name="system_status")
    def status_resource() -> str:
        return '{"status": "OK"}'

    @mcp_prompt(name="greet_user", description="Greeting prompt")
    def greeting_prompt(name: str) -> str:
        return f"Hello {name}, how can I assist you with Hexastack today?"

    runtime = bootstrap(packages_to_scan=[__name__])
    reg = get_mcp_registry()
    cfg = HexastackMcpConfig()
    server = reg.build_server(cfg, runtime.container)

    # 1. Verify list tools
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    assert "calc_tax" in tool_names
    assert "get_version" in tool_names
    assert "echo_tool" in tool_names

    # 2. Call command tool
    tax_res = await server.call_tool("calc_tax", {"amount": 100.0, "rate": 0.2})
    assert isinstance(tax_res, CallToolResult)
    tax_item = tax_res.content[0]
    assert isinstance(tax_item, TextContent)
    assert json.loads(tax_item.text) == {"tax": 20.0}

    # 3. Call query tool
    ver_res = await server.call_tool("get_version", {"component": "database"})
    assert isinstance(ver_res, CallToolResult)
    content_item = ver_res.content[0]
    assert isinstance(content_item, TextContent)
    assert content_item.text == "database-v2.0"

    # 4. Call function tool
    echo_res = await server.call_tool("echo_tool", {"msg": "hello AI"})
    assert isinstance(echo_res, CallToolResult)
    echo_item = echo_res.content[0]
    assert isinstance(echo_item, TextContent)
    assert echo_item.text == "ECHO: hello AI"
