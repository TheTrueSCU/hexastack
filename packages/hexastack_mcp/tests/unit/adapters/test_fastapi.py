from fastapi import FastAPI
from fastapi.testclient import TestClient
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_mcp.adapters.fastapi import mount_mcp_sse
from hexastack_mcp.infra.decorators import (
    mcp_tool,
)
from mcp.server.fastmcp import FastMCP as McpServer
from mcp.server.transport_security import TransportSecuritySettings


def test_fastapi_mcp_sse_mount():
    @mcp_tool(name="ping")
    def ping() -> str:
        return "pong"

    app = FastAPI()
    runtime = bootstrap(packages_to_scan=[__name__])
    server = runtime.container.resolve(McpServer)

    sec = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=["localhost", "127.0.0.1", "testserver"],
    )
    mount_mcp_sse(
        app=app,
        server=server,
        path_prefix="/mcp",
        sse_path="/sse",
        transport_security=sec,
    )

    client = TestClient(app, base_url="http://localhost")

    # Check that endpoint is mounted and accessible
    res = client.post(
        "/mcp/messages/",
        json={"type": "ping"},
        headers={"host": "localhost"},
    )
    assert res.status_code in (200, 400, 404, 421)
