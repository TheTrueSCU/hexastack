from typing import Any

from mcp.server.fastmcp import FastMCP as McpServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette


def create_mcp_sse_app(
    server: McpServer,
    sse_path: str = "/sse",
    message_path: str = "/messages/",
    transport_security: TransportSecuritySettings | None = None,
) -> Starlette:
    """Create a Starlette ASGI application handling MCP SSE transport.

    Args:
        server: Configured McpServer instance.
        sse_path: Endpoint path for SSE streams.
        message_path: Endpoint path for posting messages.
        transport_security: Optional TransportSecuritySettings instance.

    Returns:
        Starlette ASGI application.
    """
    return server.sse_app()


def mount_mcp_sse(
    app: Any,
    server: McpServer,
    path_prefix: str = "/mcp",
    sse_path: str = "/sse",
    transport_security: TransportSecuritySettings | None = None,
) -> None:
    """Mount MCP SSE endpoints onto a FastAPI/Starlette application.

    Notes/Architectural Intent:
        Enables remote LLM orchestration frameworks to connect to Hexastack
        services over HTTP SSE streams.

    Args:
        app: Target FastAPI or Starlette application.
        server: Configured McpServer instance.
        path_prefix: Route prefix where the SSE sub-app is mounted.
        sse_path: SSE stream path within the sub-app.
        transport_security: Optional TransportSecuritySettings instance.
    """
    sse_app = create_mcp_sse_app(
        server,
        sse_path=sse_path,
        transport_security=transport_security,
    )
    app.mount(path_prefix, sse_app)


__all__ = [
    "create_mcp_sse_app",
    "mount_mcp_sse",
]
