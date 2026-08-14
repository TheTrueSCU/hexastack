from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rodi import Container

from hexastack_core.infra.registries.exception import ExceptionRegistry
from hexastack_core.ports.logging import LoggingPort
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_fastapi.adapters.health import create_health_router
from hexastack_fastapi.infra.config import HexastackFastApiConfig
from hexastack_fastapi.infra.exception_handlers import (
    register_exception_handlers,
)
from hexastack_fastapi.infra.middleware.correlation import (
    CorrelationHttpMiddleware,
)
from hexastack_fastapi.infra.middleware.logging import (
    RequestLoggingHttpMiddleware,
)


def create_fastapi_app(
    config: HexastackFastApiConfig | None = None,
    container: Container | None = None,
    pipeline: ExecutionPipeline | None = None,
    exception_registry: ExceptionRegistry | None = None,
) -> FastAPI:
    """Factory creating and configuring a FastAPI application integrated with Hexastack.

    Notes/Architectural Intent:
        Assembles FastAPI instance with OpenAPI documentation metadata, CORS middleware,
        Correlation ID ASGI middleware, access logging, health check probes, unified
        exception mapping, and DI container lifecycle management.

    Args:
        config: Optional HexastackFastApiConfig instance.
        container: Optional rodi Container instance.
        pipeline: Optional ExecutionPipeline instance.
        exception_registry: Optional ExceptionRegistry for domain error mapping.

    Returns:
        Configured FastAPI application instance.

    Raises:
        None.
    """
    cfg = config or HexastackFastApiConfig()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        # Teardown background resources
        if container is not None and LoggingPort in container:
            logger = container.resolve(LoggingPort)
            close_fn = getattr(logger, "close", None)
            if callable(close_fn):
                close_fn()

    app = FastAPI(
        title=cfg.title,
        version=cfg.version,
        description=cfg.description,
        docs_url=cfg.docs_url,
        redoc_url=cfg.redoc_url,
        openapi_url=cfg.openapi_url,
        lifespan=lifespan,
    )

    # Attach container and pipeline to application state
    if container is not None:
        app.state.container = container
    if pipeline is not None:
        app.state.pipeline = pipeline

    # Attach CORS middleware if enabled
    if cfg.cors.enable:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cfg.cors.allow_origins,
            allow_credentials=cfg.cors.allow_credentials,
            allow_methods=cfg.cors.allow_methods,
            allow_headers=cfg.cors.allow_headers,
        )

    # Attach request logging middleware if enabled
    if cfg.logging.enable:
        app.add_middleware(
            RequestLoggingHttpMiddleware,
            config=cfg,
            container=container,
        )

    # Attach correlation middleware
    app.add_middleware(CorrelationHttpMiddleware, config=cfg)

    # Register unified exception handlers
    register_exception_handlers(app, exception_registry=exception_registry)

    # Mount health and readiness endpoints if enabled
    if cfg.health.enable:
        health_router = create_health_router(container=container, config=cfg.health)
        app.include_router(health_router)

    return app


__all__ = [
    "create_fastapi_app",
]
