from pydantic import BaseModel, Field

from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry


class CorsConfig(BaseModel):
    """Configuration schema for Cross-Origin Resource Sharing (CORS).

    Notes/Architectural Intent:
        Controls CORS headers, origins, allowed methods, and credential passing for REST endpoints.
    """

    enable: bool = Field(default=False)
    allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = Field(default=False)


class HealthConfig(BaseModel):
    """Configuration schema for health and readiness HTTP endpoints.

    Notes/Architectural Intent:
        Controls automatic registration of liveness and readiness probe routes for container orchestrators.
    """

    enable: bool = Field(default=True)
    health_path: str = Field(default="/health")
    ready_path: str = Field(default="/ready")


class RequestLoggingConfig(BaseModel):
    """Configuration schema for HTTP request access logging middleware.

    Notes/Architectural Intent:
        Controls emission of structured HTTP access log records with method, path, status, and duration.
    """

    enable: bool = Field(default=True)
    exclude_paths: list[str] = Field(
        default_factory=lambda: [
            "/health",
            "/ready",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
    )


@config_section("fastapi")
class HexastackFastApiConfig(BaseModel):
    """Configuration schema for FastAPI HTTP presentation adapter.

    Notes/Architectural Intent:
        Controls OpenAPI metadata, documentation routes, CORS policy, header identifiers,
        access logging, health probes, and automatic route autodiscovery.
    """

    title: str = Field(default="Hexastack API")
    version: str = Field(default="0.1.0")
    description: str = Field(default="")
    docs_url: str = Field(default="/docs")
    redoc_url: str = Field(default="/redoc")
    openapi_url: str = Field(default="/openapi.json")
    correlation_header: str = Field(default="X-Correlation-ID")
    user_header: str = Field(default="X-User-ID")
    tenant_header: str = Field(default="X-Tenant-ID")
    cors: CorsConfig = Field(default_factory=CorsConfig)
    health: HealthConfig = Field(default_factory=HealthConfig)
    logging: RequestLoggingConfig = Field(default_factory=RequestLoggingConfig)
    auto_register_routes: bool = Field(default=True)
    packages_to_scan: list[str] = Field(default_factory=list)


__all__ = [
    "CorsConfig",
    "HealthConfig",
    "HexastackFastApiConfig",
    "RequestLoggingConfig",
    "register_fastapi_config",
]


def register_fastapi_config(registry: ConfigRegistry) -> None:
    """Register FastAPI configuration schema with a ConfigRegistry under 'fastapi'.

    Args:
        registry: Target ConfigRegistry instance.

    Returns:
        None.

    Raises:
        None.
    """
    registry.register_config_section("fastapi", HexastackFastApiConfig)
