from hexastack_core.infra import ConfigRegistry
from pydantic import BaseModel, Field


class CorrelationMiddlewareConfig(BaseModel):
    """Configuration schema for CQRS correlation context middleware.

    Notes/Architectural Intent:
        Controls automatic generation and propagation of correlation IDs across message boundaries.
    """

    enable: bool = Field(default=True)
    order: int = Field(default=10)


class LoggingMiddlewareConfig(BaseModel):
    """Configuration schema for CQRS message logging middleware.

    Notes/Architectural Intent:
        Controls structured logging behavior, payload serialization, and pipeline execution order.
    """

    enable: bool = Field(default=True)
    order: int = Field(default=30)
    log_payload: bool = Field(default=True)


class RetryMiddlewareConfig(BaseModel):
    """Configuration schema for CQRS retry middleware.

    Notes/Architectural Intent:
        Controls attempt limits, circuit breaker, resilience parameters, and pipeline execution order.
    """

    enable: bool = Field(default=True)
    order: int = Field(default=50)
    max_attempts: int = Field(default=3, ge=1)
    circuit_breaker_threshold: int = Field(default=5, ge=1)
    recovery_timeout_seconds: float = Field(default=10.0, gt=0.0)


class TimingMiddlewareConfig(BaseModel):
    """Configuration schema for CQRS execution timing middleware.

    Notes/Architectural Intent:
        Controls duration tracking, threshold limits for slow execution warnings, and pipeline order.
    """

    enable_slow_warning: bool = Field(default=True)
    order: int = Field(default=20)
    slow_threshold_seconds: float = Field(default=1.0, gt=0.0)


class UnitOfWorkMiddlewareConfig(BaseModel):
    """Configuration schema for CQRS unit of work transaction middleware.

    Notes/Architectural Intent:
        Controls automatic transaction lifecycle wrapping and pipeline execution order.
    """

    enable: bool = Field(default=True)
    order: int = Field(default=40)


class CqrsMiddlewareConfig(BaseModel):
    """Container grouping configuration schemas for all CQRS middleware.

    Notes/Architectural Intent:
        Groups middleware settings under `hexastack.cqrs.middleware.<name>`.
    """

    correlation: CorrelationMiddlewareConfig = Field(
        default_factory=CorrelationMiddlewareConfig
    )
    logging: LoggingMiddlewareConfig = Field(default_factory=LoggingMiddlewareConfig)
    retry: RetryMiddlewareConfig = Field(default_factory=RetryMiddlewareConfig)
    timing: TimingMiddlewareConfig = Field(default_factory=TimingMiddlewareConfig)
    unit_of_work: UnitOfWorkMiddlewareConfig = Field(
        default_factory=UnitOfWorkMiddlewareConfig
    )


class HexastackCqrsConfig(BaseModel):
    """Top-level configuration schema for the CQRS package.

    Notes/Architectural Intent:
        Aggregates bus engine options and nested middleware configuration blocks.
    """

    use_huey_async: bool = Field(default=False)
    middleware: CqrsMiddlewareConfig = Field(default_factory=CqrsMiddlewareConfig)


def register_cqrs_config(registry: ConfigRegistry) -> None:
    """Register CQRS configuration schema with a ConfigRegistry under 'cqrs'.

    Args:
        registry: Target ConfigRegistry instance.

    Returns:
        None.

    Raises:
        None.
    """
    registry.register_config_section("cqrs", HexastackCqrsConfig)
