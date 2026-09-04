from hexastack_otel.domain.config import HexastackOtelConfig


def test_hexastack_otel_config_defaults():
    cfg = HexastackOtelConfig()
    assert cfg.service_name == "hexastack-app"
    assert cfg.endpoint == "http://localhost:4317"
    assert cfg.exporter == "memory"
    assert cfg.sample_rate == 1.0
    assert cfg.enabled is True
