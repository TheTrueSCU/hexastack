from typing import Any

from pydantic import BaseModel, Field

from hexastack_flags.domain.models import FeatureFlagProviderType


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


__all__ = [
    "HexastackFlagsConfig",
]
