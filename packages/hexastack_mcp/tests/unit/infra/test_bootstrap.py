from hexastack_core.infra.bootstrap import bootstrap
from hexastack_mcp.infra.bootstrap import (
    HexastackMcpConfig,
    McpBootstrapResult,
)
from hexastack_mcp.infra.decorators import (
    mcp_tool,
)
from mcp.server import MCPServer


def test_mcp_bootstrapper_registration():
    @mcp_tool(name="echo_tool", description="Echoes text input")
    def echo(text: str) -> str:
        return text

    runtime = bootstrap(packages_to_scan=[__name__])

    # Verify MCPServer in DI container
    server = runtime.container.resolve(MCPServer)
    assert server is not None
    assert server.name == "Hexastack MCP Server"

    # Verify result in context properties
    res = runtime.properties.get("mcp_result")
    assert isinstance(res, McpBootstrapResult)
    assert isinstance(res.config, HexastackMcpConfig)
    assert res.server is server
