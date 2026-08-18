from pydantic import BaseModel, Field

from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry


@config_section("mcp")
class HexastackMcpConfig(BaseModel):
    """Configuration schema for Hexastack Model Context Protocol (MCP) server.

    Notes/Architectural Intent:
        Controls server naming, SSE routing paths, transport security,
        and automatic FastAPI endpoint mounting.
    """

    server_name: str = Field(
        default="Hexastack MCP Server",
        description="Name of the MCP server announced to AI clients.",
    )
    server_version: str = Field(
        default="0.1.0",
        description="Version string of the MCP server.",
    )
    sse_path: str = Field(
        default="/sse",
        description="Route path for SSE transport when mounted on FastAPI.",
    )
    auto_mount_fastapi: bool = Field(
        default=True,
        description="Automatically mount SSE routes onto FastAPI application during bootstrap.",
    )
    instructions: str | None = Field(
        default="Hexastack domain service tools and resources for AI assistants.",
        description="System prompt / instructions sent to MCP client on initialization.",
    )
    enable_dns_rebinding_protection: bool = Field(
        default=True,
        description="Enable DNS rebinding protection for incoming SSE requests.",
    )
    allowed_hosts: list[str] = Field(
        default_factory=lambda: [
            "127.0.0.1:*",
            "localhost:*",
            "testserver:*",
            "testserver",
            "127.0.0.1",
            "localhost",
            "[::1]:*",
            "::1",
        ],
        description="Allowed Host header values for SSE transport security.",
    )


__all__ = [
    "HexastackMcpConfig",
    "register_mcp_config",
]


def register_mcp_config(registry: ConfigRegistry) -> None:
    """Register MCP configuration schema under 'mcp'.

    Args:
        registry: Target ConfigRegistry instance.

    Returns:
        None.
    """
    registry.register_config_section("mcp", HexastackMcpConfig)
