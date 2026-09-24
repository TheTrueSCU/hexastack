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


class ToolValidationError(ToolExecutionError):
    """Exception raised when MCP tool arguments fail validation or contain undeclared parameters.

    Notes/Architectural Intent:
        Mitigates parameter injection and tool poisoning attacks by ensuring
        strict schema matching before domain dispatch.
    """


class ToolUnauthorizedError(ToolExecutionError):
    """Exception raised when an MCP tool invocation violates permission or read-only scope constraints.

    Notes/Architectural Intent:
        Prevents Confused Deputy attacks by rejecting state-mutating commands
        in read-only server configurations or when required roles are missing.
    """


class McpAuthenticationError(McpError):
    """Exception raised when an MCP client fails transport authentication.

    Notes/Architectural Intent:
        Guards remote SSE and HTTP transport endpoints against unauthorized access.
    """


class ResourceNotFoundError(McpError):
    """Exception raised when a requested MCP resource URI is not found."""


__all__ = [
    "McpAuthenticationError",
    "McpError",
    "ResourceNotFoundError",
    "ToolExecutionError",
    "ToolUnauthorizedError",
    "ToolValidationError",
]
