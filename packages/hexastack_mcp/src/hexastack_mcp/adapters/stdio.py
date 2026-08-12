import asyncio

from mcp.server import MCPServer


async def run_stdio_async(server: MCPServer) -> None:
    """Run the MCP server over standard I/O asynchronously.

    Args:
        server: Configured MCPServer instance.
    """
    await server.run_stdio_async()


def run_stdio_server(server: MCPServer) -> None:
    """Run the MCP server synchronously over standard I/O (blocking main thread).

    Notes/Architectural Intent:
        Entrypoint for Claude Desktop, Cursor, Antigravity sidecar processes,
        and standalone CLI `hexastack mcp` commands.

    Args:
        server: Configured MCPServer instance.
    """
    asyncio.run(run_stdio_async(server))


__all__ = [
    "run_stdio_async",
    "run_stdio_server",
]
