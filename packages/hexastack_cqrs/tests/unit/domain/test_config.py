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


def test_hexastack_cqrs_config_defaults():
    cfg = HexastackCqrsConfig()
    assert cfg.use_huey_async is False
    assert isinstance(cfg.middleware, CqrsMiddlewareConfig)
    assert isinstance(cfg.middleware.circuit_breaker, CircuitBreakerMiddlewareConfig)
    assert isinstance(cfg.middleware.correlation, CorrelationMiddlewareConfig)
    assert isinstance(cfg.middleware.logging, LoggingMiddlewareConfig)
    assert isinstance(cfg.middleware.retry, RetryMiddlewareConfig)
    assert isinstance(cfg.middleware.timing, TimingMiddlewareConfig)
    assert isinstance(cfg.middleware.unit_of_work, UnitOfWorkMiddlewareConfig)
