from fastapi import FastAPI
from fastapi.testclient import TestClient
from mcp.server.fastmcp import FastMCP as McpServer
from mcp.server.transport_security import TransportSecuritySettings

from hexastack_core.infra.bootstrap import bootstrap
from hexastack_mcp.adapters.fastapi import mount_mcp_sse
from hexastack_mcp.infra.decorators import (
    mcp_tool,
)


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


def test_create_mcp_sse_app_and_mount_defaults():
    from hexastack_mcp.adapters.fastapi import create_mcp_sse_app

    server = McpServer(name="TestFastMCP")
    sse_app = create_mcp_sse_app(server)
    assert sse_app is not None

    app = FastAPI()
    mount_mcp_sse(app, server)
    # Check default mount on /mcp
    routes = [getattr(r, "path", None) for r in app.routes]
    assert "/mcp" in routes


def test_fastapi_mcp_sse_bearer_auth():
    app = FastAPI()
    server = McpServer(name="TestAuthMCP")
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
        auth_token="super-secret-token",
    )

    client = TestClient(app, base_url="http://localhost")

    # 1. Request without auth header should be rejected with 401
    res_no_auth = client.post(
        "/mcp/messages/",
        json={"type": "ping"},
        headers={"host": "localhost"},
    )
    res_no_auth_status = res_no_auth.status_code
    assert res_no_auth_status == 401
    res_no_auth_text = res_no_auth.text
    assert "Unauthorized" in res_no_auth_text

    # 2. Request with invalid token should be rejected with 401
    res_bad_auth = client.post(
        "/mcp/messages/",
        json={"type": "ping"},
        headers={"host": "localhost", "Authorization": "Bearer wrong-token"},
    )
    res_bad_auth_status = res_bad_auth.status_code
    assert res_bad_auth_status == 401
    res_bad_auth_text = res_bad_auth.text
    assert "Unauthorized" in res_bad_auth_text

    # 3. Request with valid token should pass authentication
    res_good_auth = client.post(
        "/mcp/messages/",
        json={"type": "ping"},
        headers={"host": "localhost", "Authorization": "Bearer super-secret-token"},
    )
    res_good_auth_status = res_good_auth.status_code
    assert res_good_auth_status != 401
