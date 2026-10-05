from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from rodi import Container

from hexastack_core.utils.context import get_correlation_id

__all__ = [
    "create_health_router",
]


def create_health_router(
    container: Container | None = None,
    config: Any | None = None,
    health_path: str = "/health",
    ready_path: str = "/ready",
) -> APIRouter:
    """Create APIRouter with standard liveness and readiness probe endpoints.

    Notes/Architectural Intent:
        Exposes lightweight /health (liveness) and /ready (readiness) endpoints for orchestration
        platforms like Kubernetes and container engines. Decoupled from infra configuration schemas
        by accepting primitives or duck-typed config objects.

    Args:
        container: Optional rodi Container instance to check dependency health.
        config: Optional configuration object specifying custom URL paths (e.g. HealthConfig).
        health_path: Default liveness probe path (used if config not provided).
        ready_path: Default readiness probe path (used if config not provided).

    Returns:
        APIRouter mounted with health endpoints.

    Raises:
        None.
    """
    resolved_health_path = (
        getattr(config, "health_path", None) or health_path
        if config is not None
        else health_path
    )
    resolved_ready_path = (
        getattr(config, "ready_path", None) or ready_path
        if config is not None
        else ready_path
    )
    router = APIRouter(tags=["Health"])

    @router.get(resolved_health_path, summary="Liveness Probe")
    async def liveness() -> dict[str, Any]:
        return {
            "status": "ok",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "correlation_id": get_correlation_id(),
        }

    @router.get(resolved_ready_path, summary="Readiness Probe")
    async def readiness() -> JSONResponse:
        checks: dict[str, str] = {
            "container": "ok" if container is not None else "unconfigured",
        }
        status_ok = all(v == "ok" for v in checks.values())
        payload: dict[str, Any] = {
            "status": "ready" if status_ok else "unhealthy",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "correlation_id": get_correlation_id(),
            "checks": checks,
        }
        status_code = 200 if status_ok else 503
        return JSONResponse(status_code=status_code, content=payload)

    return router
