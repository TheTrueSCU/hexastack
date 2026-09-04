from hexastack_cli.domain.config import HexastackCliConfig
from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry

config_section("cli")(HexastackCliConfig)

__all__ = [
    "HexastackCliConfig",
    "register_cli_config",
]


def register_cli_config(registry: ConfigRegistry) -> None:
    """Register CLI configuration schema with a ConfigRegistry under 'cli'.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("cli", HexastackCliConfig)
