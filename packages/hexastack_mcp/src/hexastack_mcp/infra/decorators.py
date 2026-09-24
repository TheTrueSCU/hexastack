from collections.abc import Callable, Sequence
from typing import Any

from hexastack_core.domain.query import Query
from hexastack_mcp.domain.metadata import (
    McpPromptMetadata,
    McpResourceMetadata,
    McpToolMetadata,
)
from hexastack_mcp.infra.registries.server import McpServerRegistry

_MCP_TOOL_ATTR = "__hexastack_mcp_tool__"
_MCP_RESOURCE_ATTR = "__hexastack_mcp_resource__"
_MCP_PROMPT_ATTR = "__hexastack_mcp_prompt__"

_default_registry = McpServerRegistry()


__all__ = [
    "get_mcp_registry",
    "mcp_prompt",
    "mcp_resource",
    "mcp_tool",
]


def get_mcp_registry() -> McpServerRegistry:
    """Return the global default McpServerRegistry instance.

    Returns:
        McpServerRegistry instance.
    """
    return _default_registry


def mcp_prompt(
    name: str | None = None,
    *,
    description: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator exposing a function as an MCP Prompt template.

    Args:
        name: Name of the prompt.
        description: Description of the prompt template.

    Returns:
        Decorator function.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        prompt_name = name or getattr(fn, "__name__", "prompt")
        meta = McpPromptMetadata(
            name=prompt_name,
            description=description or getattr(fn, "__doc__", None),
            handler=fn,
        )
        setattr(fn, _MCP_PROMPT_ATTR, meta)
        _default_registry.register_prompt(meta)
        return fn

    return decorator


def mcp_resource(
    uri: str,
    name: str | None = None,
    *,
    description: str | None = None,
    mime_type: str = "application/json",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator exposing a function as a readable MCP Resource.

    Args:
        uri: MCP resource URI template (e.g. 'hexastack://info').
        name: Optional resource display name.
        description: Optional resource description.
        mime_type: MIME type of the returned payload.

    Returns:
        Decorator function.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        res_name = name or getattr(fn, "__name__", "resource")
        meta = McpResourceMetadata(
            uri=uri,
            name=res_name,
            description=description or getattr(fn, "__doc__", None),
            mime_type=mime_type,
            handler=fn,
        )
        setattr(fn, _MCP_RESOURCE_ATTR, meta)
        _default_registry.register_resource(meta)
        return fn

    return decorator


def mcp_tool(
    name: str | None = None,
    *,
    description: str | None = None,
    kind: str = "command",
    read_only: bool | None = None,
    required_roles: Sequence[str] | None = None,
) -> Callable[[Any], Any]:
    """Decorator exposing a Command class, Query class, or function as an MCP Tool.

    Notes/Architectural Intent:
        Attaches discovery metadata for single-pass module scanning and registers
        the tool in the default McpServerRegistry. Supports least-privilege scoping
        via read_only and required_roles attributes.

    Args:
        name: Name of the tool presented to AI agents. Defaults to kebab/snake class name.
        description: Description of tool utility.
        kind: 'command', 'query', or 'function'.
        read_only: Explicit flag indicating whether tool is side-effect-free. Defaults to True for queries.
        required_roles: Optional sequence of role or permission scopes required to invoke the tool.

    Returns:
        Decorator function.
    """

    def decorator(target: Any) -> Any:
        tool_name = name or getattr(target, "__name__", "tool")
        is_query_subclass = isinstance(target, type) and issubclass(target, Query)
        is_read_only = (
            read_only
            if read_only is not None
            else (kind == "query" or is_query_subclass)
        )
        meta = McpToolMetadata(
            name=tool_name,
            description=description or getattr(target, "__doc__", None),
            kind=kind,
            target=target,
            read_only=is_read_only,
            required_roles=tuple(required_roles) if required_roles else (),
        )
        setattr(target, _MCP_TOOL_ATTR, meta)
        _default_registry.register_tool(meta)
        return target

    return decorator
