from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_fastapi.infra.config import (
    CorsConfig,
    HealthConfig,
    HexastackFastApiConfig,
    RequestLoggingConfig,
    register_fastapi_config,
)


def test_register_fastapi_config():
    reg = ConfigRegistry()
    register_fastapi_config(reg)

    assert "fastapi" in reg
    assert reg.get("fastapi") == HexastackFastApiConfig


def test_fastapi_config_defaults():
    cfg = HexastackFastApiConfig()

    assert cfg.title == "Hexastack API"
    assert cfg.version == "0.1.0"
    assert cfg.correlation_header == "X-Correlation-ID"
    assert cfg.cors.enable is False
    assert cfg.health.enable is True
    assert cfg.logging.enable is True
    assert cfg.auto_register_routes is True


def test_fastapi_config_custom():
    cfg = HexastackFastApiConfig.model_validate(
        {
            "title": "Custom App",
            "cors": {"enable": True, "allow_origins": ["https://example.com"]},
            "health": {"enable": False, "health_path": "/status"},
            "logging": {"enable": False},
        }
    )

    assert cfg.title == "Custom App"
    assert cfg.cors.enable is True
    assert cfg.cors.allow_origins == ["https://example.com"]
    assert isinstance(cfg.cors, CorsConfig)
    assert cfg.health.enable is False
    assert cfg.health.health_path == "/status"
    assert isinstance(cfg.health, HealthConfig)
    assert cfg.logging.enable is False
    assert isinstance(cfg.logging, RequestLoggingConfig)
