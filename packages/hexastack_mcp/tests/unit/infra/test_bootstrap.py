import pytest
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_mcp.infra.decorators import (
    get_mcp_registry,
    mcp_tool,
)
from mcp.server import MCPServer


@pytest.fixture(autouse=True)
def clean_registry():
    reg = get_mcp_registry()
    reg.clear()
    yield
    reg.clear()


def test_mcp_bootstrapper_registration():
    @mcp_tool(name="health_check")
    def health() -> str:
        return "healthy"

    runtime = bootstrap(packages_to_scan=[__name__])

    # Verify MCPServer resolved in container
    server = runtime.container.resolve(MCPServer)
    assert server is not None
    assert server.name == "Hexastack MCP Server"

    # Verify context properties
    assert "mcp_server" in runtime.properties
    assert "mcp_result" in runtime.properties
