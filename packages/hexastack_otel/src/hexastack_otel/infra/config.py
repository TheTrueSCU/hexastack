from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_otel.domain.config import HexastackOtelConfig

config_section("otel")(HexastackOtelConfig)

__all__ = [
    "HexastackOtelConfig",
    "register_otel_config",
]


def register_otel_config(registry: ConfigRegistry) -> None:
    """Register the OpenTelemetry config section schema in ConfigRegistry.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("otel", HexastackOtelConfig)
