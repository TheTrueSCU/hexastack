from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from hexastack_core.domain import HexastackError
from hexastack_core.infra.registries.exception import ExceptionRegistry
from hexastack_core.utils.context import get_correlation_id


def register_exception_handlers(
    app: FastAPI,
    exception_registry: ExceptionRegistry | None = None,
) -> None:
    """Register unified exception handlers translating domain errors into HTTP responses.

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
        elif "unauthorized" in exc_name or "forbidden" in exc_name:
            status_code = 401
        elif "validation" in exc_name:
            status_code = 422

        content: dict[str, Any] = {
            "error": str(exc),
            "error_type": exc.__class__.__name__,
            "correlation_id": get_correlation_id(),
        }
        return JSONResponse(status_code=status_code, content=content)


__all__ = [
    "register_exception_handlers",
]
