from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_events.infra.config import (
    HexastackEventsConfig,
    register_events_config,
)


def test_events_config_custom_values():
    cfg = HexastackEventsConfig(
        source="custom-service",
        relay_mode="huey",
        poll_interval_seconds=0.5,
        batch_size=100,
        max_retries=10,
        enabled=False,
    )
    assert cfg.source == "custom-service"
    assert cfg.relay_mode == "huey"
    assert cfg.poll_interval_seconds == 0.5
    assert cfg.batch_size == 100
    assert cfg.max_retries == 10
    assert cfg.enabled is False


def test_events_config_defaults():
    cfg = HexastackEventsConfig()
    assert cfg.source == "hexastack-app"
    assert cfg.relay_mode == "asyncio"
    assert cfg.poll_interval_seconds == 1.0
    assert cfg.batch_size == 50
    assert cfg.max_retries == 5
    assert cfg.enabled is True


def test_register_events_config():
    reg = ConfigRegistry()
    register_events_config(reg)
    assert "events" in reg
    schema = reg.get("events")
    assert schema is HexastackEventsConfig
