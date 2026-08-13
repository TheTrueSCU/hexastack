import importlib.util
from dataclasses import dataclass

from hexastack_core.infra.bootstrap import (
    BootstrapContext,
)
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from mcp.server.fastmcp import FastMCP as McpServer
from mcp.server.transport_security import TransportSecuritySettings

from hexastack_mcp.infra.autodiscovery import create_mcp_visitor
from hexastack_mcp.infra.config import (
    HexastackMcpConfig,
    register_mcp_config,
)
from hexastack_mcp.infra.decorators import get_mcp_registry
from hexastack_mcp.infra.registries.server import McpServerRegistry


@dataclass(frozen=True)
class McpBootstrapResult:
    """Dataclass holding initialized MCP server and configuration."""

    config: HexastackMcpConfig
    server: McpServer
    registry: McpServerRegistry


class McpBootstrapper(BootstrapperPort):
    """Bootstrap extension configuring Anthropic Model Context Protocol (MCP) server.

    Notes/Architectural Intent:
        Implements BootstrapperPort with order=40 (executing after CQRS order=20
        and FastAPI order=30), registering the autodiscovery visitor, assembling
        the McpServer instance with CQRS tool wrappers, and mounting SSE endpoints
        onto FastAPI when present.
    """

    name: str = "mcp"
    order: int = 40

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Register visitor, assemble McpServer, and mount SSE endpoints.

        Args:
            context: BootstrapContext containing DI container, config, and properties.

        Returns:
            None.
        """
        cfg = context.get_config("mcp", HexastackMcpConfig)

        registry = get_mcp_registry()

        # Register visitor for single-pass reflective scanning (Phase 3)
        visitor = create_mcp_visitor(registry)
        context.register_visitor(visitor)

        # 1. Build McpServer instance from registry and container
        server = registry.build_server(config=cfg, container=context.container)

        # 2. Register Server and Registry into DI container
        context.container.add_instance(server, declared_class=McpServer)
        context.container.add_instance(registry)

        # 3. Mount onto FastAPI app if available and configured
        if cfg.auto_mount_fastapi and importlib.util.find_spec("fastapi") is not None:
            fastapi_app = context.properties.get("app")
            if fastapi_app is not None:
                from hexastack_mcp.adapters.fastapi import mount_mcp_sse

                sec = TransportSecuritySettings(
                    enable_dns_rebinding_protection=cfg.enable_dns_rebinding_protection,
                    allowed_hosts=cfg.allowed_hosts,
                )
                mount_mcp_sse(
                    app=fastapi_app,
                    server=server,
                    path_prefix=cfg.sse_path,
                    transport_security=sec,
                )

        # 4. Store in context properties
        result = McpBootstrapResult(
            config=cfg,
            server=server,
            registry=registry,
        )
        context.properties["mcp_result"] = result
        context.properties["mcp_server"] = server

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register MCP configuration schema under 'mcp'.

        Args:
            registry: Target ConfigRegistry instance.

        Returns:
            None.
        """
        register_mcp_config(registry)


__all__ = [
    "McpBootstrapResult",
    "McpBootstrapper",
]
