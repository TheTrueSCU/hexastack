from collections.abc import Callable
from typing import Any

import grpc

from hexastack_core.domain.exceptions import HexastackError
from hexastack_grpc.infra.interceptors.generic import (
    AsyncGenericServerInterceptor,
    GenericServerInterceptor,
)


class ExceptionServerInterceptor(GenericServerInterceptor):
    """Synchronous gRPC Server Interceptor mapping domain exceptions to gRPC status codes.

    Notes/Architectural Intent:
        Intercepts unhandled HexastackError domain exceptions and aborts the RPC
        call with appropriate native gRPC StatusCodes (NOT_FOUND, INVALID_ARGUMENT, etc.).
    """

    def _handle_unary(
        self,
        request: Any,
        context: grpc.ServicerContext,
        unary_fn: Callable[[Any, grpc.ServicerContext], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Invoke the unary handler, aborting the RPC on any domain exception."""
        try:
            return unary_fn(request, context)
        except Exception as exc:  # noqa: BLE001
            status_code, details = _map_exception_to_status_code(exc)
            context.abort(status_code, details)


class AsyncExceptionServerInterceptor(AsyncGenericServerInterceptor):
    """Asynchronous gRPC Server Interceptor mapping domain exceptions to gRPC status codes."""

    async def _handle_unary_async(
        self,
        request: Any,
        context: grpc.aio.ServicerContext,
        unary_fn: Callable[[Any, grpc.aio.ServicerContext], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Invoke the async unary handler, aborting the RPC on any domain exception."""
        try:
            return await unary_fn(request, context)
        except Exception as exc:  # noqa: BLE001
            status_code, details = _map_exception_to_status_code(exc)
            await context.abort(status_code, details)


__all__ = [
    "AsyncExceptionServerInterceptor",
    "ExceptionServerInterceptor",
]


def _map_exception_to_status_code(exc: Exception) -> tuple[grpc.StatusCode, str]:
    """Map domain exceptions to gRPC status codes and detail messages."""
    exc_name = type(exc).__name__.lower()
    msg = str(exc)

    if "notfound" in exc_name:
        return grpc.StatusCode.NOT_FOUND, msg
    if "validation" in exc_name or "invalid" in exc_name:
        return grpc.StatusCode.INVALID_ARGUMENT, msg
    if "unauthorized" in exc_name or "authentication" in exc_name:
        return grpc.StatusCode.UNAUTHENTICATED, msg
    if "forbidden" in exc_name or "permission" in exc_name:
        return grpc.StatusCode.PERMISSION_DENIED, msg
    if "conflict" in exc_name or "alreadyexists" in exc_name:
        return grpc.StatusCode.ALREADY_EXISTS, msg
    if isinstance(exc, HexastackError):
        return grpc.StatusCode.INTERNAL, msg

    return grpc.StatusCode.UNKNOWN, msg
