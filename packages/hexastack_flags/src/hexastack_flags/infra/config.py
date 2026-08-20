"""Configuration schemas for hexastack-flags.

Notes/Architectural Intent:
    Defines Pydantic configuration schemas loaded from [hexastack.flags].
"""

from typing import Any

from pydantic import BaseModel, Field

from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_flags.domain.models import FeatureFlagProviderType

__all__ = [
    "HexastackFlagsConfig",
    "register_flags_config",
]


@config_section("flags")
class HexastackFlagsConfig(BaseModel):
    """Configuration options under [hexastack.flags]."""

    provider: str = Field(
        default=FeatureFlagProviderType.IN_MEMORY.value,
        description="Feature flag provider backend: 'flagd', 'in_memory', 'env'",
    )
    host: str = Field(default="localhost", description="Flagd server hostname")
    port: int = Field(default=8013, description="Flagd server port")
    cache: bool = Field(
        default=True, description="Enable local in-memory evaluation cache"
    )
    timeout_ms: int = Field(
        default=5000, description="Evaluation timeout in milliseconds"
    )
    flags: dict[str, Any] = Field(
        default_factory=dict,
        description="Static in-memory feature flags mapping (key -> bool/value)",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific configuration options",
    )


def register_flags_config(registry: ConfigRegistry) -> None:
    """Register the flags configuration schema with the ConfigRegistry."""
    registry.register_config_section("flags", HexastackFlagsConfig)
