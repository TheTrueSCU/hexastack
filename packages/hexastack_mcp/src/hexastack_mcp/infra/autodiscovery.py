from collections.abc import Sequence
from types import ModuleType
from typing import Any

from hexastack_core.infra.autodiscovery import (
    DiscoveryVisitor,
    scan_modules,
)

from hexastack_mcp.domain.metadata import (
    McpPromptMetadata,
    McpResourceMetadata,
    McpToolMetadata,
)
from hexastack_mcp.infra.decorators import (
    _MCP_PROMPT_ATTR,
    _MCP_RESOURCE_ATTR,
    _MCP_TOOL_ATTR,
)
from hexastack_mcp.infra.registries.server import McpServerRegistry


def create_mcp_visitor(
    registry: McpServerRegistry,
) -> DiscoveryVisitor:
    """Create a DiscoveryVisitor callback for single-pass MCP element discovery.

    Notes/Architectural Intent:
        Inspects discovered classes and functions for MCP tool, resource, and prompt
        decorator metadata, registering them into the supplied server registry
        during single-pass reflection.

    Args:
        registry: Target McpServerRegistry instance.

    Returns:
        DiscoveryVisitor callable accepting (member, module).
    """

    def visitor(obj: Any, module: ModuleType) -> None:
        tool_meta: McpToolMetadata | None = getattr(obj, _MCP_TOOL_ATTR, None)
        if tool_meta is not None:
            registry.register_tool(tool_meta)

        res_meta: McpResourceMetadata | None = getattr(obj, _MCP_RESOURCE_ATTR, None)
        if res_meta is not None:
            registry.register_resource(res_meta)

        prompt_meta: McpPromptMetadata | None = getattr(obj, _MCP_PROMPT_ATTR, None)
        if prompt_meta is not None:
            registry.register_prompt(prompt_meta)

    return visitor


def autodiscover_mcp_elements(
    packages_to_scan: Sequence[str | ModuleType],
    registry: McpServerRegistry,
) -> McpServerRegistry:
    """Discover decorated MCP tools, resources, and prompts from packages.

    Args:
        packages_to_scan: Sequence of package names or module objects to inspect.
        registry: Target McpServerRegistry instance.

    Returns:
        The populated McpServerRegistry instance.
    """
    visitor = create_mcp_visitor(registry)
    scan_modules(packages_to_scan, [visitor])
    return registry


__all__ = [
    "autodiscover_mcp_elements",
    "create_mcp_visitor",
]
