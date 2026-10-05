import inspect
import json
import logging
import platform
import sys
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP as McpServer
from mcp.server.transport_security import TransportSecuritySettings
from rodi import Container

from hexastack_core.domain.command import Command
from hexastack_core.utils.inspection import inspect_model_parameters
from hexastack_cqrs.ports.buses import (
    CommandBusPort,
    QueryBusPort,
)
from hexastack_mcp.domain.exceptions import (
    ToolExecutionError,
    ToolUnauthorizedError,
    ToolValidationError,
)
from hexastack_mcp.domain.metadata import (
    McpPromptMetadata,
    McpResourceMetadata,
    McpToolMetadata,
)
from hexastack_mcp.infra.config import HexastackMcpConfig

logger = logging.getLogger(__name__)


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

    def _create_cqrs_tool_wrapper(
        self,
        target_cls: type[Any],
        kind: str,
        container: Container,
        read_only_tool: bool = False,
        server_read_only: bool = False,
    ) -> Callable[..., Any]:
        """Synthesize a typed callable from a Command or Query class for MCP schema generation.

        Notes/Architectural Intent:
            Enforces strict parameter validation by rejecting unexpected kwargs,
            guarantees read-only invariants to mitigate Confused Deputy attacks,
            and sanitizes internal exception traces to prevent secret leakage.

        Args:
            target_cls: Target Command or Query class.
            kind: 'command' or 'query'.
            container: DI container resolving bus ports.
            read_only_tool: Whether tool is marked read-only.
            server_read_only: Whether server enforces read-only mode.

        Returns:
            Callable tool wrapper compatible with FastMCP.
        """
        parameters = inspect_model_parameters(target_cls)
        declared_param_names = {p.name for p in parameters}

        async def dynamic_mcp_tool(**kwargs: Any) -> Any:
            if server_read_only and not read_only_tool:
                raise ToolUnauthorizedError(
                    f"Tool '{target_cls.__name__}' is rejected: MCP server is operating in read-only mode."
                )

            unexpected_params = set(kwargs.keys()) - declared_param_names
            if unexpected_params:
                raise ToolValidationError(
                    f"Unexpected parameters for MCP tool '{target_cls.__name__}': {sorted(unexpected_params)}. "
                    f"Allowed parameters: {sorted(declared_param_names)}"
                )

            try:
                instance = target_cls(**kwargs)
                return await self._dispatch_cqrs_instance(
                    instance, target_cls, kind, container
                )
            except (ToolValidationError, ToolUnauthorizedError):
                raise
            except (ValueError, TypeError) as exc:
                raise ToolValidationError(
                    f"Validation failed for MCP tool '{target_cls.__name__}': {exc}"
                ) from exc
            except Exception as exc:
                logger.exception(
                    "Internal failure executing MCP tool '%s'", target_cls.__name__
                )
                raise ToolExecutionError(
                    f"Internal error executing MCP tool '{target_cls.__name__}'. Please check server logs."
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

    async def _dispatch_cqrs_instance(
        self,
        instance: Any,
        target_cls: type[Any],
        kind: str,
        container: Container,
    ) -> Any:
        """Resolve bus from container and dispatch command/query instance."""
        if kind == "command" or issubclass(target_cls, Command):
            cbus = container.resolve(CommandBusPort)
            result = cbus.dispatch(instance)
        else:
            qbus = container.resolve(QueryBusPort)
            result = qbus.dispatch(instance)

        if inspect.isawaitable(result):
            result = await result
        return result

    def _mount_prompts(self, server: McpServer) -> None:
        """Register all prompt templates onto McpServer instance."""
        for prompt_meta in self._prompts:
            if prompt_meta.handler is not None:
                server.prompt(
                    name=prompt_meta.name,
                    description=prompt_meta.description,
                )(prompt_meta.handler)

    def _mount_resources(self, server: McpServer) -> None:
        """Register all resource endpoints onto McpServer instance."""
        for res_meta in self._resources:
            if res_meta.handler is not None:
                server.resource(
                    uri=res_meta.uri,
                    name=res_meta.name,
                    description=res_meta.description,
                    mime_type=res_meta.mime_type,
                )(res_meta.handler)

    def _mount_tools(
        self,
        server: McpServer,
        container: Container,
        config: HexastackMcpConfig | None = None,
    ) -> None:
        """Register all tool wrappers onto McpServer instance.

        Notes/Architectural Intent:
            Filters out mutating command tools if the MCP server operates in
            read-only mode.

        Args:
            server: McpServer instance to mount tools onto.
            container: DI Container for dependency resolution.
            config: Optional HexastackMcpConfig for read-only evaluation.
        """
        server_read_only = bool(config and config.read_only)
        for tool_meta in self._tools:
            if server_read_only and not tool_meta.read_only:
                logger.info(
                    "Skipping tool '%s' because MCP server is operating in read-only mode.",
                    tool_meta.name,
                )
                continue

            if inspect.isclass(tool_meta.target):
                tool_fn = self._create_cqrs_tool_wrapper(
                    target_cls=tool_meta.target,
                    kind=tool_meta.kind,
                    container=container,
                    read_only_tool=tool_meta.read_only,
                    server_read_only=server_read_only,
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

    def _register_diagnostic_resources(
        self, server: McpServer, config: HexastackMcpConfig
    ) -> None:
        """Register built-in system and registry diagnostic resources."""

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
        sec = TransportSecuritySettings(
            enable_dns_rebinding_protection=config.enable_dns_rebinding_protection,
            allowed_hosts=list(config.allowed_hosts),
        )
        server = McpServer(
            name=config.server_name,
            instructions=config.instructions,
            transport_security=sec,
        )

        self._register_diagnostic_resources(server, config)
        self._mount_tools(server, container, config=config)
        self._mount_resources(server)
        self._mount_prompts(server)

        return server

    @property
    def prompts(self) -> list[McpPromptMetadata]:
        return list(self._prompts)

    def register_prompt(self, meta: McpPromptMetadata) -> None:
        """Register prompt template metadata.

        Args:
            meta: McpPromptMetadata instance.
        """
        if meta not in self._prompts:
            self._prompts.append(meta)

    def register_resource(self, meta: McpResourceMetadata) -> None:
        """Register resource metadata.

        Args:
            meta: McpResourceMetadata instance.
        """
        if meta not in self._resources:
            self._resources.append(meta)

    def register_tool(self, meta: McpToolMetadata) -> None:
        """Register tool metadata.

        Args:
            meta: McpToolMetadata instance.
        """
        if meta not in self._tools:
            self._tools.append(meta)

    @property
    def resources(self) -> list[McpResourceMetadata]:
        return list(self._resources)

    @property
    def tools(self) -> list[McpToolMetadata]:
        return list(self._tools)


__all__ = [
    "McpServerRegistry",
]
