from typing import Any

from mcp.server.fastmcp import FastMCP as McpServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

__all__ = [
    "create_mcp_sse_app",
    "mount_mcp_sse",
]


class _BearerAuthMiddleware(BaseHTTPMiddleware):
    """ASGI middleware enforcing Bearer token authentication on MCP HTTP endpoints.

    Notes/Architectural Intent:
        Guards remote SSE and message endpoints against unauthorized requests.
    """

    def __init__(self, app: Any, auth_token: str) -> None:
        super().__init__(app)
        self._auth_token = auth_token

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        auth_header = request.headers.get("Authorization", "")
        expected = f"Bearer {self._auth_token}"
        if auth_header.strip() != expected:
            return PlainTextResponse(
                "Unauthorized: Invalid or missing Bearer token", status_code=401
            )
        return await call_next(request)


def create_mcp_sse_app(
    server: McpServer,
    sse_path: str = "/sse",
    message_path: str = "/messages/",
    transport_security: TransportSecuritySettings | None = None,
    auth_token: str | None = None,
) -> Starlette:
    """Create a Starlette ASGI application handling MCP SSE transport.

    Notes/Architectural Intent:
        Wraps FastMCP SSE application with transport security and optional Bearer
        token authentication middleware to secure remote MCP exposure.

    Args:
        server: Configured McpServer instance.
        sse_path: Endpoint path for SSE streams.
        message_path: Endpoint path for posting messages.
        transport_security: Optional TransportSecuritySettings instance.
        auth_token: Optional shared secret required as a Bearer token.

    Returns:
        Starlette ASGI application.
    """
    if transport_security is not None:
        server.settings.transport_security = transport_security

    sse_app = server.sse_app()
    if auth_token:
        sse_app.add_middleware(_BearerAuthMiddleware, auth_token=auth_token)

    return sse_app


def mount_mcp_sse(
    app: Any,
    server: McpServer,
    path_prefix: str = "/mcp",
    sse_path: str = "/sse",
    transport_security: TransportSecuritySettings | None = None,
    auth_token: str | None = None,
) -> None:
    """Mount MCP SSE endpoints onto a FastAPI/Starlette application.

    Notes/Architectural Intent:
        Enables remote LLM orchestration frameworks to connect to Hexastack
        services over HTTP SSE streams with optional token authentication.

    Args:
        app: Target FastAPI or Starlette application.
        server: Configured McpServer instance.
        path_prefix: Route prefix where the SSE sub-app is mounted.
        sse_path: SSE stream path within the sub-app.
        transport_security: Optional TransportSecuritySettings instance.
        auth_token: Optional shared secret required as a Bearer token.
    """
    sse_app = create_mcp_sse_app(
        server,
        sse_path=sse_path,
        transport_security=transport_security,
        auth_token=auth_token,
    )
    app.mount(path_prefix, sse_app)
