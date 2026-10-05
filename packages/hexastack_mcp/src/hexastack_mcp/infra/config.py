from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_mcp.domain.config import HexastackMcpConfig

config_section("mcp")(HexastackMcpConfig)

__all__ = [
    "HexastackMcpConfig",
    "register_mcp_config",
]


def register_mcp_config(registry: ConfigRegistry) -> None:
    """Register MCP configuration schema under 'mcp'.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("mcp", HexastackMcpConfig)
