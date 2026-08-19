import json
from dataclasses import dataclass

import pytest
from mcp.types import TextContent

from hexastack_core.domain.command import Command
from hexastack_core.domain.query import Query
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_cqrs.infra.decorators import command_handler, query_handler
from hexastack_mcp.domain.exceptions import ToolExecutionError
from hexastack_mcp.domain.metadata import (
    McpPromptMetadata,
    McpResourceMetadata,
    McpToolMetadata,
)
from hexastack_mcp.infra.config import HexastackMcpConfig
from hexastack_mcp.infra.decorators import (
    get_mcp_registry,
    mcp_prompt,
    mcp_resource,
    mcp_tool,
)
from hexastack_mcp.infra.registries.server import McpServerRegistry


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


@dataclass(frozen=True)
class FailingCommand(Command):
    message: str


@command_handler(FailingCommand)
class FailingHandler:
    def __call__(self, cmd: FailingCommand) -> None:
        raise ValueError(f"Failing explicitly: {cmd.message}")


@dataclass(frozen=True)
class AsyncEchoQuery(Query):
    text: str


@query_handler(AsyncEchoQuery)
class AsyncEchoHandler:
    async def __call__(self, qry: AsyncEchoQuery) -> str:
        return f"Async echo: {qry.text}"


@pytest.mark.anyio
async def test_mcp_server_registry_tools_execution():
    @mcp_tool(name="calc_tax", description="Calculate tax for an amount")
    class TaxCmd(CalculateTaxCommand):
        pass

    @mcp_tool(name="get_version", kind="query")
    class VersionQry(GetServerVersionQuery):
        pass

    @mcp_tool(name="async_echo_tool", kind="query")
    class AsyncQry(AsyncEchoQuery):
        pass

    @mcp_tool(name="failing_tool", kind="command")
    class FailCmd(FailingCommand):
        pass

    @mcp_tool(name="registry_echo_tool")
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
    cfg = HexastackMcpConfig(
        server_name="Hexastack-Test-Server", instructions="Test instructions"
    )
    server = reg.build_server(cfg, runtime.container)

    # 1. Verify list tools
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    assert "calc_tax" in tool_names
    assert "get_version" in tool_names
    assert "async_echo_tool" in tool_names
    assert "failing_tool" in tool_names
    assert "registry_echo_tool" in tool_names

    # 2. Call command tool
    tax_res = await server.call_tool("calc_tax", {"amount": 100.0, "rate": 0.2})
    assert isinstance(tax_res, list) and len(tax_res) > 0
    tax_item = tax_res[0]
    assert isinstance(tax_item, TextContent)
    assert json.loads(tax_item.text) == {"tax": 20.0}

    # 3. Call query tool
    ver_res = await server.call_tool("get_version", {"component": "database"})
    assert isinstance(ver_res, list) and len(ver_res) > 0
    content_item = ver_res[0]
    assert isinstance(content_item, TextContent)
    assert content_item.text == "database-v2.0"

    # 4. Call async query tool
    async_res = await server.call_tool("async_echo_tool", {"text": "stream"})
    assert isinstance(async_res, list) and len(async_res) > 0
    async_item = async_res[0]
    assert isinstance(async_item, TextContent)
    assert async_item.text == "Async echo: stream"

    # 5. Call function tool
    echo_raw = await server.call_tool("registry_echo_tool", {"msg": "hello AI"})
    echo_res = echo_raw[0] if isinstance(echo_raw, tuple) else echo_raw
    assert isinstance(echo_res, list) and len(echo_res) > 0
    echo_item = echo_res[0]
    assert isinstance(echo_item, TextContent)
    assert echo_item.text == "ECHO: hello AI"

    # 6. Failing tool wrapper directly raises ToolExecutionError
    cqrs_wrapper = reg._create_cqrs_tool_wrapper(FailCmd, "command", runtime.container)
    with pytest.raises(ToolExecutionError) as exc_info:
        await cqrs_wrapper(message="boom")
    assert "Execution of MCP tool 'FailCmd' failed: Failing explicitly: boom" in str(
        exc_info.value
    )

    # 7. Built-in diagnostic resources
    resources = await server.list_resources()
    resource_uris = [str(r.uri) for r in resources]
    assert "hexastack://info" in resource_uris
    assert "hexastack://registry" in resource_uris
    assert "hexastack://status" in resource_uris

    info_raw = await server.read_resource("hexastack://info")
    info_text = str(info_raw[0].content if isinstance(info_raw, list) else info_raw)
    info_json = json.loads(info_text)
    assert info_json["server_name"] == "Hexastack-Test-Server"
    assert "python_version" in info_json
    assert info_json["tools_count"] >= 5

    manifest_raw = await server.read_resource("hexastack://registry")
    manifest_text = str(
        manifest_raw[0].content if isinstance(manifest_raw, list) else manifest_raw
    )
    manifest_json = json.loads(manifest_text)
    assert len(manifest_json["tools"]) >= 5
    assert len(manifest_json["resources"]) >= 1
    assert len(manifest_json["prompts"]) >= 1

    # 8. Prompts listing and properties
    prompts = await server.list_prompts()
    prompt_names = [p.name for p in prompts]
    assert "greet_user" in prompt_names


def test_mcp_server_registry_registration_idempotency_and_properties():
    """Verify registry getters, properties, and idempotency of registration."""
    reg = McpServerRegistry()
    assert reg.tools == []
    assert reg.resources == []
    assert reg.prompts == []

    tool_meta = McpToolMetadata(name="t1", target=lambda: "t1", kind="function")
    res_meta = McpResourceMetadata(uri="test://res", name="r1", handler=lambda: "res")
    prompt_meta = McpPromptMetadata(name="p1", handler=lambda: "p1")

    reg.register_tool(tool_meta)
    reg.register_tool(tool_meta)  # Duplicate registration ignored
    assert len(reg.tools) == 1
    assert reg.tools[0].name == "t1"

    reg.register_resource(res_meta)
    reg.register_resource(res_meta)  # Duplicate ignored
    assert len(reg.resources) == 1
    assert reg.resources[0].uri == "test://res"

    reg.register_prompt(prompt_meta)
    reg.register_prompt(prompt_meta)  # Duplicate ignored
    assert len(reg.prompts) == 1
    assert reg.prompts[0].name == "p1"
