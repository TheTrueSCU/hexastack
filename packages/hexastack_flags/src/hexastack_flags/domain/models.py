"""Domain models and enumerations for OpenFeature integration.

Notes/Architectural Intent:
    Encapsulates OpenFeature provider types, provider options, and evaluation
    metadata conforming to the CNCF OpenFeature specification.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "FeatureFlagProviderType",
    "FlagProviderOptions",
]


class FeatureFlagProviderType(StrEnum):
    """Supported CNCF OpenFeature provider backends."""

    FLAGD = "flagd"
    IN_MEMORY = "in_memory"
    ENV = "env"
    CUSTOM = "custom"


class FlagProviderOptions(BaseModel):
    """Configuration options for OpenFeature provider initialization."""

    host: str = "localhost"
    port: int = 8013
    cache: bool = True
    timeout_ms: int = 5000
    extra: dict[str, Any] = Field(default_factory=dict)
