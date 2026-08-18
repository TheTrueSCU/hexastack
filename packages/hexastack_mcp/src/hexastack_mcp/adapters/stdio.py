import asyncio

from mcp.server.fastmcp import FastMCP as McpServer

__all__ = [
    "run_stdio_async",
    "run_stdio_server",
]


async def run_stdio_async(server: McpServer) -> None:
    """Asynchronously execute the MCP stdio communication loop.

    Args:
        server: Configured McpServer instance.
    """
    await server.run_stdio_async()


def run_stdio_server(server: McpServer) -> None:
    """Synchronously execute the MCP stdio communication loop via asyncio.run().

    Notes/Architectural Intent:
        Standard entrypoint for CLI stdio execution when orchestrated by
        Claude Desktop, Cursor, or external LLM tool executors.

    Args:
        server: Configured McpServer instance.
    """
    asyncio.run(run_stdio_async(server))
