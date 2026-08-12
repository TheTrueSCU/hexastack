from hexastack_core.infra import ConfigRegistry
from pydantic import BaseModel, Field


class RetryMiddlewareConfig(BaseModel):
    """Configuration schema for CQRS retry middleware.

    Notes/Architectural Intent:
        Controls attempt limits and resilience parameters for command/query execution.
    """

    enable: bool = Field(default=True)
    max_attempts: int = Field(default=3, ge=1)
    circuit_breaker_threshold: int = Field(default=5, ge=1)
    recovery_timeout_seconds: float = Field(default=10.0, gt=0.0)


class TimingMiddlewareConfig(BaseModel):
    """Configuration schema for CQRS execution timing middleware.

    Notes/Architectural Intent:
        Controls duration tracking and threshold limits for slow execution warnings.
    """

    enable_slow_warning: bool = Field(default=True)
    slow_threshold_seconds: float = Field(default=1.0, gt=0.0)


class LoggingMiddlewareConfig(BaseModel):
    """Configuration schema for CQRS message logging middleware.

    Notes/Architectural Intent:
        Controls structured logging behavior and payload serialization toggles.
    """

    enable: bool = Field(default=True)
    log_payload: bool = Field(default=True)


class CqrsMiddlewareConfig(BaseModel):
    """Container grouping configuration schemas for all CQRS middleware.

    Notes/Architectural Intent:
        Groups middleware settings under `hexastack.cqrs.middleware.<name>`.
    """

    logging: LoggingMiddlewareConfig = Field(default_factory=LoggingMiddlewareConfig)
    retry: RetryMiddlewareConfig = Field(default_factory=RetryMiddlewareConfig)
    timing: TimingMiddlewareConfig = Field(default_factory=TimingMiddlewareConfig)


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
