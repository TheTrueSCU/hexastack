from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from hexastack_core.domain import HexastackError
from hexastack_core.infra.registries.exception import ExceptionRegistry
from hexastack_core.utils.context import get_correlation_id

__all__ = [
    "register_exception_handlers",
]


def register_exception_handlers(
    app: FastAPI,
    exception_registry: ExceptionRegistry | None = None,
) -> None:
    """Register unified exception handlers translating domain errors into HTTP responses.

    Notes/Architectural Intent:
        Intercepts HexastackError domain exceptions and unhandled system errors.
        Maps domain errors to standardized HTTP status codes (400, 401, 403, 404, 409, 422)
        and forwards unhandled 500 exceptions with correlation ID and request tags to Sentry if active.

    Args:
        app: Target FastAPI application instance.
        exception_registry: Optional ExceptionRegistry for custom exception mappings.

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

        status_code = 400
        exc_name = exc.__class__.__name__.lower()
        if "notfound" in exc_name:
            status_code = 404
        elif "conflict" in exc_name or "duplicate" in exc_name:
            status_code = 409
        elif (
            "permission" in exc_name
            or "forbidden" in exc_name
            or "accessdenied" in exc_name
        ):
            status_code = 403
        elif (
            "unauthorized" in exc_name
            or "unauthenticated" in exc_name
            or "invalidcredential" in exc_name
        ):
            status_code = 401
        elif "validation" in exc_name:
            status_code = 422

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
        try:
            import sentry_sdk

            with sentry_sdk.push_scope() as scope:
                scope.set_tag("path", request.url.path)
                scope.set_tag("method", request.method)
                if correlation_id:
                    scope.set_tag("correlation_id", correlation_id)
                sentry_sdk.capture_exception(exc)
        except Exception:
            pass

        content: dict[str, Any] = {
            "error": "Internal server error",
            "error_type": exc.__class__.__name__,
            "correlation_id": correlation_id,
        }
        return JSONResponse(status_code=500, content=content)
