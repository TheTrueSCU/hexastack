from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_otel.infra.config import (
    HexastackOtelConfig,
    register_otel_config,
)


def test_otel_config_defaults():
    cfg = HexastackOtelConfig()
    assert cfg.service_name == "hexastack-app"
    assert cfg.endpoint == "http://localhost:4317"
    assert cfg.exporter == "memory"
    assert cfg.sample_rate == 1.0
    assert cfg.enabled is True


def test_register_otel_config():
    reg = ConfigRegistry()
    register_otel_config(reg)
    assert "otel" in reg
    schema = reg.get("otel")
    assert schema is HexastackOtelConfig
