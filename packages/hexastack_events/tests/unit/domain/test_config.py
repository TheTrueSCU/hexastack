from hexastack_events.domain.config import HexastackEventsConfig


def test_hexastack_events_config_defaults():
    cfg = HexastackEventsConfig()
    assert cfg.source == "hexastack-app"
    assert cfg.relay_mode == "asyncio"
    assert cfg.poll_interval_seconds == 1.0
    assert cfg.batch_size == 50
    assert cfg.max_retries == 5
    assert cfg.enabled is True
