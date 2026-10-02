"""ASGI middleware for capturing HTTP request rate and duration metrics."""

from __future__ import annotations

import time

from rodi import Container
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.ports.metrics import MetricsPort
from hexastack_fastapi.infra.config import HexastackFastApiConfig


class HttpMetricsMiddleware:
    """ASGI middleware recording HTTP RED (Rate, Errors, Duration) metrics.

    Notes/Architectural Intent:
        Intercepts incoming HTTP transactions, measures duration, and updates
        MetricsPort counters and histograms. Guards metric emission via FeatureFlagPort.
    """

    def __init__(
        self,
        app: ASGIApp,
        config: HexastackFastApiConfig | None = None,
        container: Container | None = None,
        metrics: MetricsPort | None = None,
        flags: FeatureFlagPort | None = None,
    ) -> None:
        """Initialize HTTP metrics middleware.

        Args:
            app: Downstream ASGI application.
            config: Optional HexastackFastApiConfig instance.
            container: Optional rodi Container to dynamically resolve MetricsPort / FeatureFlagPort.
            metrics: Optional pre-configured MetricsPort instance.
            flags: Optional FeatureFlagPort instance.
        """
        self._app = app
        self._cfg = config or HexastackFastApiConfig()
        self._container = container
        self._metrics = metrics
        self._flags = flags
        self._exclude_paths = set(self._cfg.logging.exclude_paths)

    def _get_metrics(self) -> MetricsPort | None:
        if self._metrics is not None:
            return self._metrics
        if self._container is not None and MetricsPort in self._container:
            return self._container.resolve(MetricsPort)
        return None

    def _get_flags(self) -> FeatureFlagPort | None:
        if self._flags is not None:
            return self._flags
        if self._container is not None and FeatureFlagPort in self._container:
            return self._container.resolve(FeatureFlagPort)
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Intercept request, measure duration, and record metrics."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "/")
        if path in self._exclude_paths or path == "/metrics":
            await self._app(scope, receive, send)
            return

        metrics = self._get_metrics()
        if metrics is None:
            await self._app(scope, receive, send)
            return

        flags = self._get_flags()
        if flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not flags.is_enabled(
                "features.metrics.http", default=True, context=eval_ctx
            ):
                await self._app(scope, receive, send)
                return

        method = scope.get("method", "GET")
        status_code = 500
        start_time = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start_time
            labels = {
                "method": method,
                "path": path,
                "status_code": str(status_code),
            }
            metrics.increment_counter(
                "http_requests_total",
                value=1.0,
                labels=labels,
                description="Total HTTP requests processed",
            )
            metrics.record_histogram(
                "http_request_duration_seconds",
                value=duration,
                labels={"method": method, "path": path},
                description="HTTP request duration distribution in seconds",
            )


__all__ = [
    "HttpMetricsMiddleware",
]
