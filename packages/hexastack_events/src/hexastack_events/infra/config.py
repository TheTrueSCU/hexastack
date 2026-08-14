from typing import Literal

from pydantic import BaseModel, Field

from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry


@config_section("events")
class HexastackEventsConfig(BaseModel):
    """Pydantic configuration model for event streaming and transactional outbox.

    Notes/Architectural Intent:
        Configured via `[hexastack.events]` in pyproject.toml or hexastack.toml.
        Controls relay engine mode (asyncio, huey, manual) and batching limits.
    """

    source: str = Field(
        default="hexastack-app",
        description="Logical service identifier attached to all CloudEvents envelopes.",
    )
    relay_mode: Literal["asyncio", "huey", "manual", "disabled"] = Field(
        default="asyncio",
        description="Outbox relay execution mode ('asyncio', 'huey', 'manual', 'disabled').",
    )
    poll_interval_seconds: float = Field(
        default=1.0,
        description="Frequency in seconds to poll pending outbox records.",
    )
    batch_size: int = Field(
        default=50,
        description="Maximum number of outbox events to drain per cycle.",
    )
    max_retries: int = Field(
        default=5,
        description="Maximum failed attempts before an outbox record is abandoned.",
    )
    enabled: bool = Field(
        default=True,
        description="Master switch to activate event streaming subsystem.",
    )


def register_events_config(registry: ConfigRegistry) -> None:
    """Register the events configuration section in ConfigRegistry.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("events", HexastackEventsConfig)


__all__ = [
    "HexastackEventsConfig",
    "register_events_config",
]
