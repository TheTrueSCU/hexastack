import time

from rodi import Container
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from hexastack_core.adapters.logging.standard import StandardLogger
from hexastack_core.ports.logging import LoggingPort
from hexastack_fastapi.infra.config import HexastackFastApiConfig


class RequestLoggingHttpMiddleware:
    """ASGI middleware producing structured access logs for HTTP requests.

    Notes/Architectural Intent:
        Measures HTTP transaction duration, captures client metadata and response status,
        and logs via the LoggingPort resolved from the DI container.
    """

    def __init__(
        self,
        app: ASGIApp,
        config: HexastackFastApiConfig | None = None,
        container: Container | None = None,
        logger: LoggingPort | None = None,
    ) -> None:
        """Initialize request logging middleware.

        Args:
            app: Downstream ASGI application.
            config: Optional HexastackFastApiConfig instance.
            container: Optional rodi Container to dynamically resolve LoggingPort.
            logger: Optional pre-configured LoggingPort instance.
        """
        self._app = app
        self._cfg = config or HexastackFastApiConfig()
        self._container = container
        self._logger = logger or StandardLogger("hexastack.http")
        self._exclude_paths = set(self._cfg.logging.exclude_paths)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Intercept request, measure duration, and log access details."""
        if scope["type"] != "http" or not self._cfg.logging.enable:
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "/")
        if path in self._exclude_paths:
            await self._app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        http_version = scope.get("http_version", "1.1")
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        status_code = 500
        start_time = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)
        finally:
            end_time = time.perf_counter()
            duration_ms = round((end_time - start_time) * 1000, 2)
            log = self._get_logger()
            msg = f"{method} {path} HTTP/{http_version} -> {status_code} ({duration_ms}ms)"
            extra = {
                "http_method": method,
                "http_path": path,
                "http_status": status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            }
            if status_code >= 500:
                log.error(msg, extra=extra)
            elif status_code >= 400:
                log.warning(msg, extra=extra)
            else:
                log.info(msg, extra=extra)

    def _get_logger(self) -> LoggingPort:
        """Resolve LoggingPort from container if available, else use fallback."""
        if self._container is not None and LoggingPort in self._container:
            return self._container.resolve(LoggingPort)
        return self._logger


__all__ = [
    "RequestLoggingHttpMiddleware",
]
