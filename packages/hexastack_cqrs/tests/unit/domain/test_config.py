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

    # CircuitBreaker
    cb = cfg.middleware.circuit_breaker
    assert isinstance(cb, CircuitBreakerMiddlewareConfig)
    assert cb.enable is True
    assert cb.order == 45
    assert cb.failure_threshold == 5
    assert cb.recovery_timeout_seconds == 10.0
    assert cb.half_open_max_trials == 1

    # Correlation
    corr = cfg.middleware.correlation
    assert isinstance(corr, CorrelationMiddlewareConfig)
    assert corr.enable is True
    assert corr.order == 10

    # Logging
    log = cfg.middleware.logging
    assert isinstance(log, LoggingMiddlewareConfig)
    assert log.enable is True
    assert log.order == 30
    assert log.log_payload is True

    # Retry
    retry = cfg.middleware.retry
    assert isinstance(retry, RetryMiddlewareConfig)
    assert retry.enable is True
    assert retry.order == 50
    assert retry.max_attempts == 3
    assert retry.initial_backoff_seconds == 0.1
    assert retry.max_backoff_seconds == 5.0
    assert retry.jitter is True
    assert retry.circuit_breaker_threshold == 5
    assert retry.recovery_timeout_seconds == 10.0

    # Timing
    timing = cfg.middleware.timing
    assert isinstance(timing, TimingMiddlewareConfig)
    assert timing.enable_slow_warning is True
    assert timing.order == 20
    assert timing.slow_threshold_seconds == 1.0

    # UnitOfWork
    uow = cfg.middleware.unit_of_work
    assert isinstance(uow, UnitOfWorkMiddlewareConfig)
    assert uow.enable is True
    assert uow.order == 40
