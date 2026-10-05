from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_cqrs.domain.config import (
    CircuitBreakerMiddlewareConfig,
    CorrelationMiddlewareConfig,
    CqrsMiddlewareConfig,
    HexastackCqrsConfig,
    LoggingMiddlewareConfig,
    RetryMiddlewareConfig,
    TimingMiddlewareConfig,
    UnitOfWorkMiddlewareConfig,
)

config_section("cqrs")(HexastackCqrsConfig)

__all__ = [
    "CircuitBreakerMiddlewareConfig",
    "CorrelationMiddlewareConfig",
    "CqrsMiddlewareConfig",
    "HexastackCqrsConfig",
    "LoggingMiddlewareConfig",
    "register_cqrs_config",
    "RetryMiddlewareConfig",
    "TimingMiddlewareConfig",
    "UnitOfWorkMiddlewareConfig",
]


def register_cqrs_config(registry: ConfigRegistry) -> None:
    """Register CQRS configuration schema with a ConfigRegistry under 'cqrs'.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("cqrs", HexastackCqrsConfig)
