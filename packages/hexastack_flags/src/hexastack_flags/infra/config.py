from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_flags.domain.config import HexastackFlagsConfig

config_section("flags")(HexastackFlagsConfig)

__all__ = [
    "HexastackFlagsConfig",
    "register_flags_config",
]


def register_flags_config(registry: ConfigRegistry) -> None:
    """Register the flags configuration schema with the ConfigRegistry."""
    registry.register_config_section("flags", HexastackFlagsConfig)
