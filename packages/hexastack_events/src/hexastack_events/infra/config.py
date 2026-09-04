from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_events.domain.config import HexastackEventsConfig

config_section("events")(HexastackEventsConfig)

__all__ = [
    "HexastackEventsConfig",
    "register_events_config",
]


def register_events_config(registry: ConfigRegistry) -> None:
    """Register the events configuration section in ConfigRegistry.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("events", HexastackEventsConfig)
