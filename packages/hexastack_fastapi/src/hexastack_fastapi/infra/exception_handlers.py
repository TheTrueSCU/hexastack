import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from hexastack_core.domain import HexastackError
from hexastack_core.infra.registries.exception import ExceptionRegistry
from hexastack_core.ports.logging import LoggingPort
from hexastack_core.utils.context import get_correlation_id

_fallback_logger = logging.getLogger(__name__)

__all__ = [
    "register_exception_handlers",
]


def _infer_status_code(exc: HexastackError) -> int:
    """Infer HTTP status code from domain exception class name.

    Args:
        exc: Domain error instance.

    Returns:
        Standard HTTP status code matching error semantics.
    """
    exc_name = exc.__class__.__name__.lower()
    if "notfound" in exc_name:
        return 404
    if "conflict" in exc_name or "duplicate" in exc_name:
        return 409
    if any(k in exc_name for k in ("permission", "forbidden", "accessdenied")):
        return 403
    if any(
        k in exc_name for k in ("unauthorized", "unauthenticated", "invalidcredential")
    ):
        return 401
    if "validation" in exc_name:
        return 422
    return 400


def _resolve_logger(app: FastAPI, explicit: LoggingPort | None) -> LoggingPort | None:
    """Resolve LoggingPort from explicit argument or FastAPI application container.

    Args:
        app: Target FastAPI application.
        explicit: Optional explicitly supplied LoggingPort instance.

    Returns:
        Resolved LoggingPort or None.
    """
    if explicit is not None:
        return explicit
    container = getattr(app.state, "container", None)
    if container is not None and LoggingPort in container:
        return container.resolve(LoggingPort)
    return None


def _forward_to_sentry(
    request: Request,
    exc: Exception,
    correlation_id: str | None,
    active_logger: LoggingPort | None,
) -> None:
    """Forward unhandled exception context to Sentry SDK if installed and configured.

    Args:
        request: FastAPI HTTP request instance.
        exc: Unhandled exception.
        correlation_id: Optional correlation trace identifier.
        active_logger: Optional LoggingPort for diagnostic telemetry.
    """
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("path", request.url.path)
            scope.set_tag("method", request.method)
            if correlation_id:
                scope.set_tag("correlation_id", correlation_id)
            sentry_sdk.capture_exception(exc)
    except Exception as sentry_exc:  # noqa: BLE001
        if active_logger is not None:
            active_logger.debug(f"Failed to forward exception to Sentry: {sentry_exc}")
        else:
            _fallback_logger.debug(
                "Failed to forward exception to Sentry: %s", sentry_exc
            )


def register_exception_handlers(
    app: FastAPI,
    exception_registry: ExceptionRegistry | None = None,
    logger: LoggingPort | None = None,
) -> None:
    """Register unified exception handlers translating domain errors into HTTP responses.

    Notes/Architectural Intent:
        Intercepts HexastackError domain exceptions and unhandled system errors.
        Maps domain errors to standardized HTTP status codes (400, 401, 403, 404, 409, 422)
        and forwards unhandled 500 exceptions with correlation ID and request tags to Sentry if active.

    Args:
        app: Target FastAPI application instance.
        exception_registry: Optional ExceptionRegistry for custom exception mappings.
        logger: Optional LoggingPort instance to receive exception forwarding diagnostics.

    Returns:
        None.

    Raises:
        None.
    """

    @app.exception_handler(HexastackError)
    async def hexastack_error_handler(
        request: Request, exc: HexastackError
    ) -> JSONResponse:
        """Handle HexastackError subclasses with status code inference and correlation metadata."""
        if exception_registry is not None and type(exc) in exception_registry:
            mapped = exception_registry.handle(exc)
            if isinstance(mapped, dict) and "status_code" in mapped:
                status = mapped.pop("status_code")
                return JSONResponse(status_code=status, content=mapped)
            return JSONResponse(status_code=400, content=mapped)

        status_code = _infer_status_code(exc)
        content: dict[str, Any] = {
            "error": str(exc),
            "error_type": exc.__class__.__name__,
            "correlation_id": get_correlation_id(),
        }
        return JSONResponse(status_code=status_code, content=content)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unhandled server exceptions, push context to Sentry if available, and return 500."""
        correlation_id = get_correlation_id()
        active_logger = _resolve_logger(app, logger)
        _forward_to_sentry(request, exc, correlation_id, active_logger)

        content: dict[str, Any] = {
            "error": "Internal server error",
            "error_type": exc.__class__.__name__,
            "correlation_id": correlation_id,
        }
        return JSONResponse(status_code=500, content=content)
