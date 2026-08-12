from hexastack_core.domain.exceptions import HexastackError


class McpError(HexastackError):
    """Base exception for all Model Context Protocol (MCP) adapter errors.

    Notes/Architectural Intent:
        Maintains consistency across the unified Hexastack exception tree.
    """


class ToolExecutionError(McpError):
    """Exception raised when an MCP tool execution fails.

    Notes/Architectural Intent:
        Carries context when command or query dispatching from an MCP client
        encounters an error.
    """


class ResourceNotFoundError(McpError):
    """Exception raised when a requested MCP resource URI is not found."""


__all__ = [
    "McpError",
    "ResourceNotFoundError",
    "ToolExecutionError",
]
