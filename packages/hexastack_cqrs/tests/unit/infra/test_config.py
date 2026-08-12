from hexastack_core.infra import ConfigRegistry
from hexastack_cqrs.infra.config import (
    HexastackCqrsConfig,
    register_cqrs_config,
)


def test_register_cqrs_config():
    registry = ConfigRegistry()
    register_cqrs_config(registry)

    assert registry.get("cqrs") == HexastackCqrsConfig


def test_default_cqrs_config():
    config = HexastackCqrsConfig()
    assert config.use_huey_async is False
    assert config.middleware.retry.enable is True
    assert config.middleware.retry.max_attempts == 3
    assert config.middleware.retry.circuit_breaker_threshold == 5
    assert config.middleware.retry.recovery_timeout_seconds == 10.0
    assert config.middleware.timing.enable_slow_warning is True
    assert config.middleware.timing.slow_threshold_seconds == 1.0
    assert config.middleware.logging.enable is True
    assert config.middleware.logging.log_payload is True
