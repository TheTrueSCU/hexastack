import inspect
import json
import platform
import sys
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP as McpServer
from rodi import Container

from hexastack_core.domain.command import Command
from hexastack_core.utils.inspection import inspect_model_parameters
from hexastack_cqrs.ports.buses import (
    CommandBusPort,
    QueryBusPort,
)
from hexastack_mcp.domain.exceptions import ToolExecutionError
from hexastack_mcp.domain.metadata import (
    McpPromptMetadata,
    McpResourceMetadata,
    McpToolMetadata,
)
from hexastack_mcp.infra.config import HexastackMcpConfig


class McpServerRegistry:
    """Registry maintaining registered MCP tools, resources, and prompt templates.

    Notes/Architectural Intent:
        Compiles declarative tool and resource definitions into an McpServer
        (FastMCP) instance, binding CQRS dispatchers from the rodi DI Container.
    """

    def __init__(self) -> None:
        """Initialize empty MCP registry."""
        self._tools: list[McpToolMetadata] = []
        self._resources: list[McpResourceMetadata] = []
        self._prompts: list[McpPromptMetadata] = []

    def register_tool(self, meta: McpToolMetadata) -> None:
        """Register tool metadata.

        Args:
            meta: McpToolMetadata instance.
        """
        if meta not in self._tools:
            self._tools.append(meta)

    def register_resource(self, meta: McpResourceMetadata) -> None:
        """Register resource metadata.

        Args:
            meta: McpResourceMetadata instance.
        """
        if meta not in self._resources:
            self._resources.append(meta)

    def register_prompt(self, meta: McpPromptMetadata) -> None:
        """Register prompt template metadata.

        Args:
            meta: McpPromptMetadata instance.
        """
        if meta not in self._prompts:
            self._prompts.append(meta)

    @property
    def tools(self) -> list[McpToolMetadata]:
        return list(self._tools)

    @property
    def resources(self) -> list[McpResourceMetadata]:
        return list(self._resources)

    @property
    def prompts(self) -> list[McpPromptMetadata]:
        return list(self._prompts)

    def _create_cqrs_tool_wrapper(
        self,
        target_cls: type[Any],
        kind: str,
        container: Container,
    ) -> Callable[..., Any]:
        """Synthesize a typed callable from a Command or Query class for MCP schema generation."""
        # 1. Extract parameter definitions
        parameters = inspect_model_parameters(target_cls)

        async def dynamic_mcp_tool(**kwargs: Any) -> Any:
            try:
                instance = target_cls(**kwargs)
                if kind == "command" or issubclass(target_cls, Command):
                    cbus = container.resolve(CommandBusPort)
                    result = cbus.dispatch(instance)
                else:
                    qbus = container.resolve(QueryBusPort)
                    result = qbus.dispatch(instance)

                if inspect.isawaitable(result):
                    result = await result
                return result
            except Exception as exc:
                raise ToolExecutionError(
                    f"Execution of MCP tool '{target_cls.__name__}' failed: {exc}"
                ) from exc

        # Set dynamic signature & annotations
        setattr(  # noqa: B010
            dynamic_mcp_tool,
            "__signature__",
            inspect.Signature(parameters=parameters),
        )
        dynamic_mcp_tool.__annotations__ = {p.name: p.annotation for p in parameters}
        dynamic_mcp_tool.__name__ = target_cls.__name__
        dynamic_mcp_tool.__doc__ = target_cls.__doc__
        return dynamic_mcp_tool

    def build_server(
        self,
        config: HexastackMcpConfig,
        container: Container,
    ) -> McpServer:
        """Construct and populate an McpServer instance from registered elements.

        Args:
            config: HexastackMcpConfig options.
            container: Active rodi DI container for dependency resolution.

        Returns:
            Configured McpServer instance.
        """
        server = McpServer(
            name=config.server_name,
            instructions=config.instructions,
        )

        # 1. Built-in Diagnostic Resources
        @server.resource(
            uri="hexastack://info",
            name="system_info",
            description="System platform and Hexastack framework runtime diagnostic information.",
            mime_type="application/json",
        )
        def get_system_info_resource() -> str:
            return json.dumps(
                {
                    "platform": platform.platform(),
                    "python_version": sys.version,
                    "server_name": config.server_name,
                    "tools_count": len(self._tools),
                    "resources_count": len(self._resources),
                    "prompts_count": len(self._prompts),
                },
                indent=2,
            )

        @server.resource(
            uri="hexastack://registry",
            name="registry_manifest",
            description="Manifest of all registered tools, resources, and prompt templates in Hexastack.",
            mime_type="application/json",
        )
        def get_registry_manifest_resource() -> str:
            return json.dumps(
                {
                    "tools": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "kind": t.kind,
                        }
                        for t in self._tools
                    ],
                    "resources": [
                        {
                            "uri": r.uri,
                            "name": r.name,
                            "description": r.description,
                        }
                        for r in self._resources
                    ],
                    "prompts": [
                        {"name": p.name, "description": p.description}
                        for p in self._prompts
                    ],
                },
                indent=2,
            )

        # 2. Register Tools
        for tool_meta in self._tools:
            if inspect.isclass(tool_meta.target):
                tool_fn = self._create_cqrs_tool_wrapper(
                    target_cls=tool_meta.target,
                    kind=tool_meta.kind,
                    container=container,
                )
                server.add_tool(
                    tool_fn,
                    name=tool_meta.name,
                    description=tool_meta.description or tool_fn.__doc__,
                )
            elif callable(tool_meta.target):
                server.add_tool(
                    tool_meta.target,
                    name=tool_meta.name,
                    description=tool_meta.description or tool_meta.target.__doc__,
                )

        # 3. Register Resources
        for res_meta in self._resources:
            if res_meta.handler is not None:
                server.resource(
                    uri=res_meta.uri,
                    name=res_meta.name,
                    description=res_meta.description,
                    mime_type=res_meta.mime_type,
                )(res_meta.handler)

        # 4. Register Prompts
        for prompt_meta in self._prompts:
            if prompt_meta.handler is not None:
                server.prompt(
                    name=prompt_meta.name,
                    description=prompt_meta.description,
                )(prompt_meta.handler)

        return server


__all__ = [
    "McpServerRegistry",
]
