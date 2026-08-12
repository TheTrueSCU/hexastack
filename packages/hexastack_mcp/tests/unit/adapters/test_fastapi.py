import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_mcp.adapters.fastapi import mount_mcp_sse
from hexastack_mcp.infra.decorators import (
    get_mcp_registry,
    mcp_tool,
)
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings


@pytest.fixture(autouse=True)
def clean_registry():
    reg = get_mcp_registry()
    reg.clear()
    yield
    reg.clear()


def test_fastapi_mcp_sse_mount():
    @mcp_tool(name="ping")
    def ping() -> str:
        return "pong"

    app = FastAPI()
    runtime = bootstrap(packages_to_scan=[__name__])
    server = runtime.container.resolve(MCPServer)

    sec = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    )
    mount_mcp_sse(
        app=app,
        server=server,
        path_prefix="/mcp",
        sse_path="/sse",
        transport_security=sec,
    )

    client = TestClient(app)

    # Check that endpoint is mounted and accessible
    # POST to messages without valid session returns 400 Bad Request
    res = client.post("/mcp/messages/", json={"type": "ping"})
    assert res.status_code in (200, 400)
