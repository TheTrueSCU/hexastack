from typing import Literal

from pydantic import BaseModel, Field

from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry


@config_section("otel")
class HexastackOtelConfig(BaseModel):
    """Pydantic configuration model for OpenTelemetry tracing subsystem.

    Notes/Architectural Intent:
        Configured via `[hexastack.otel]` in pyproject.toml or hexastack.toml.
        Supports in-memory, console, and gRPC/HTTP OTLP exporters.
    """

    service_name: str = Field(
        default="hexastack-app",
        description="Logical service name identifier attached to all telemetry spans.",
    )
    endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP collector endpoint URL (e.g. 'http://localhost:4317' or 'http://tempo:4317').",
    )
    exporter: Literal["memory", "console", "otlp_grpc", "otlp_http"] = Field(
        default="memory",
        description="Target span exporter backend ('memory', 'console', 'otlp_grpc', 'otlp_http').",
    )
    sample_rate: float = Field(
        default=1.0,
        description="Sampling probability ratio between 0.0 and 1.0.",
    )
    enabled: bool = Field(
        default=True,
        description="Master switch to activate or bypass tracing middleware.",
    )


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
