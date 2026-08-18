from hexastack_core.infra import ConfigRegistry
from hexastack_cqrs.infra.config import (
    HexastackCqrsConfig,
    register_cqrs_config,
)


def test_default_cqrs_config():
    config = HexastackCqrsConfig()
    assert config.use_huey_async is False
    assert config.middleware.correlation.enable is True
    assert config.middleware.correlation.order == 10
    assert config.middleware.timing.enable_slow_warning is True
    assert config.middleware.timing.order == 20
    assert config.middleware.timing.slow_threshold_seconds == 1.0
    assert config.middleware.logging.enable is True
    assert config.middleware.logging.order == 30
    assert config.middleware.logging.log_payload is True
    assert config.middleware.unit_of_work.enable is True
    assert config.middleware.unit_of_work.order == 40
    assert config.middleware.retry.enable is True
    assert config.middleware.retry.order == 50
    assert config.middleware.retry.max_attempts == 3
    assert config.middleware.retry.circuit_breaker_threshold == 5
    assert config.middleware.retry.recovery_timeout_seconds == 10.0


def test_register_cqrs_config():
    registry = ConfigRegistry()
    register_cqrs_config(registry)

    assert registry.get("cqrs") == HexastackCqrsConfig
