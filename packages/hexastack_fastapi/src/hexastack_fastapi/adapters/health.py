from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from hexastack_core.utils.context import get_correlation_id
from rodi import Container

from hexastack_fastapi.infra.config import HealthConfig


def create_health_router(
    container: Container | None = None,
    config: HealthConfig | None = None,
) -> APIRouter:
    """Create APIRouter with standard liveness and readiness probe endpoints.

    Notes/Architectural Intent:
        Exposes lightweight /health (liveness) and /ready (readiness) endpoints for orchestration
        platforms like Kubernetes and container engines.

    Args:
        container: Optional rodi Container instance to check dependency health.
        config: Optional HealthConfig specifying custom URL paths.

    Returns:
        APIRouter mounted with health endpoints.

    Raises:
        None.
    """
    cfg = config or HealthConfig()
    router = APIRouter(tags=["Health"])

    @router.get(cfg.health_path, summary="Liveness Probe")
    async def liveness() -> dict[str, Any]:
        return {
            "status": "ok",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "correlation_id": get_correlation_id(),
        }

    @router.get(cfg.ready_path, summary="Readiness Probe")
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


__all__ = [
    "create_health_router",
]
