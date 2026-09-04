from hexastack_fastapi.domain.config import (
    CorsConfig,
    HealthConfig,
    HexastackFastApiConfig,
    RateLimitConfig,
    RequestLoggingConfig,
    ZensicalDocsConfig,
)


def test_hexastack_fastapi_config_defaults():
    cfg = HexastackFastApiConfig()
    assert cfg.title == "Hexastack API"
    assert cfg.version == "0.1.0"
    assert isinstance(cfg.cors, CorsConfig)
    assert isinstance(cfg.health, HealthConfig)
    assert isinstance(cfg.logging, RequestLoggingConfig)
    assert isinstance(cfg.ratelimit, RateLimitConfig)
    assert isinstance(cfg.zensical, ZensicalDocsConfig)
