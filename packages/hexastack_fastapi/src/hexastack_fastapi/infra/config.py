from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_fastapi.domain.config import (
    CorsConfig,
    HealthConfig,
    HexastackFastApiConfig,
    RateLimitConfig,
    RequestLoggingConfig,
    ZensicalDocsConfig,
)

config_section("fastapi")(HexastackFastApiConfig)

__all__ = [
    "CorsConfig",
    "HealthConfig",
    "HexastackFastApiConfig",
    "RateLimitConfig",
    "register_fastapi_config",
    "RequestLoggingConfig",
    "ZensicalDocsConfig",
]


def register_fastapi_config(registry: ConfigRegistry) -> None:
    """Register FastAPI configuration schema with a ConfigRegistry under 'fastapi'.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("fastapi", HexastackFastApiConfig)
