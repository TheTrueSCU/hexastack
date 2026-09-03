"""Prometheus Metrics Endpoint Router for FastAPI."""

from __future__ import annotations

from fastapi import APIRouter, Response
from rodi import Container

from hexastack_core.ports.metrics import MetricsPort


def create_metrics_router(container: Container | None = None) -> APIRouter:
    """Create a FastAPI APIRouter mounting the /metrics Prometheus scraper endpoint.

    Args:
        container: Active rodi Container to resolve MetricsPort.

    Returns:
        APIRouter exposing GET /metrics.
    """
    router = APIRouter(tags=["Observability"])

    @router.get("/metrics", include_in_schema=False)
    async def get_metrics() -> Response:
        if container is not None and MetricsPort in container:
            metrics_port = container.resolve(MetricsPort)
            body = metrics_port.generate_metrics_text()
        else:
            try:
                from prometheus_client import generate_latest

                body = generate_latest()
            except ImportError:
                body = b"# Prometheus metrics not configured"

        return Response(
            content=body, media_type="text/plain; version=0.0.4; charset=utf-8"
        )

    return router


__all__ = [
    "create_metrics_router",
]
