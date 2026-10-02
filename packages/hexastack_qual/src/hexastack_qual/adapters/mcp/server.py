"""MCP server runner for hexastack-qual.

Notes/Architectural Intent:
    Configures and starts the Model Context Protocol server exposing quality
    tools over stdio (for CLI agents/Claude Desktop) or SSE.
"""

from __future__ import annotations

from typing import Any

from hexastack_qual.adapters.mcp.tools import register_quality_mcp_tools
from hexastack_qual.domain.exceptions import AdapterNotAvailableError

try:
    import rodi

    from hexastack_mcp.adapters.stdio import run_stdio_async
    from hexastack_mcp.domain.config import HexastackMcpConfig
    from hexastack_mcp.infra.registries.server import McpServerRegistry

    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    McpServerRegistry = None  # type: ignore[misc,assignment]


def create_quality_mcp_server(
    registry: McpServerRegistry | None = None,
    server_name: str = "hexastack-qual",
    container: Any | None = None,
) -> Any:
    """Create and configure an MCP server with quality tools and resources.

    Args:
        registry: Optional pre-configured McpServerRegistry.
        server_name: Name of the FastMCP server.
        container: Optional rodi.Container for dependency injection.

    Returns:
        Built FastMCP server instance.

    Raises:
        AdapterNotAvailableError: If hexastack-mcp is not installed.
    """
    if not HAS_MCP:
        raise AdapterNotAvailableError(
            extra_name="mcp",
            install_command="pip install 'hexastack-qual[mcp]'",
        )

    if registry is not None:
        reg = registry
    else:
        from hexastack_mcp.infra.registries.server import McpServerRegistry

        reg = McpServerRegistry()
    register_quality_mcp_tools(reg)
    cfg = HexastackMcpConfig(server_name=server_name)
    cnt = container or rodi.Container()
    return reg.build_server(config=cfg, container=cnt)


async def run_quality_mcp_server() -> None:
    """Run the quality MCP server over stdio.

    Raises:
        AdapterNotAvailableError: If hexastack-mcp is not installed.
    """
    server = create_quality_mcp_server()
    await run_stdio_async(server)


__all__ = [
    "create_quality_mcp_server",
    "run_quality_mcp_server",
]
