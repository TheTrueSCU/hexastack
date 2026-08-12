from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class McpToolMetadata:
    """Metadata for exposing a Command, Query, or function as an MCP Tool.

    Notes/Architectural Intent:
        Parsed by McpServerRegistry and single-pass autodiscovery visitors
        to register MCP tools on the FastMCP/MCP server.
    """

    name: str
    description: str | None = None
    kind: str = "command"  # "command", "query", or "function"
    target: Any | None = None


@dataclass(frozen=True)
class McpResourceMetadata:
    """Metadata for exposing data or endpoints as an MCP Resource."""

    uri: str
    name: str
    description: str | None = None
    mime_type: str = "application/json"
    handler: Callable[..., Any] | None = None


@dataclass(frozen=True)
class McpPromptMetadata:
    """Metadata for exposing prompt templates to AI agents."""

    name: str
    description: str | None = None
    handler: Callable[..., Any] | None = None


__all__ = [
    "McpPromptMetadata",
    "McpResourceMetadata",
    "McpToolMetadata",
]
