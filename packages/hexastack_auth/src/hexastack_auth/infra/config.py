from hexastack_auth.domain.config import (
    HexastackAuthConfig,
    OpaConfig,
    OpenFgaConfig,
    SpiffeConfig,
)
from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry

config_section("auth")(HexastackAuthConfig)

__all__ = [
    "HexastackAuthConfig",
    "OpaConfig",
    "OpenFgaConfig",
    "register_auth_config",
    "SpiffeConfig",
]


def register_auth_config(registry: ConfigRegistry) -> None:
    """Register the auth configuration section in the global ConfigRegistry.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("auth", HexastackAuthConfig)
