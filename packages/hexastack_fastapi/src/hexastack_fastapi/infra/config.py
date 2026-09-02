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


class RateLimitConfig(BaseModel):
    """Configuration schema for rate limiting and request quota enforcement.

    Notes/Architectural Intent:
        Controls global and endpoint-level rate limits, key extraction strategy
        (IP, user_id, tenant_id), and storage backend connection.
    """

    enable: bool = Field(default=False)
    default_limits: list[str] = Field(default_factory=lambda: ["100/minute"])
    key_func: str = Field(
        default="ip",
        description="Key extraction strategy: 'ip', 'user', 'tenant', or 'combined'.",
    )
    storage_uri: str = Field(
        default="memory://",
        description="Backend storage URI: 'memory://' or 'redis://localhost:6379'.",
    )


class ZensicalDocsConfig(BaseModel):
    """Configuration schema for mounting pre-built Zensical documentation onto FastAPI.

    Notes/Architectural Intent:
        Controls automatic mounting of Zensical static documentation site.
        Default mount path is `/guide` to prevent collision with OpenAPI Swagger UI at `/docs`.
    """

    enable: bool = Field(default=False)
    path: str = Field(default="/guide")
    site_dir: str = Field(default="site")


@config_section("fastapi")
class HexastackFastApiConfig(BaseModel):
    """Configuration schema for FastAPI HTTP presentation adapter.

    Notes/Architectural Intent:
        Controls OpenAPI metadata, documentation routes, CORS policy, header identifiers,
        access logging, health probes, Zensical docs mounting, and automatic route autodiscovery.
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
    ratelimit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    zensical: ZensicalDocsConfig = Field(default_factory=ZensicalDocsConfig)
    auto_register_routes: bool = Field(default=True)
    packages_to_scan: list[str] = Field(default_factory=list)


__all__ = [
    "CorsConfig",
    "HealthConfig",
    "HexastackFastApiConfig",
    "RateLimitConfig",
    "RequestLoggingConfig",
    "ZensicalDocsConfig",
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
