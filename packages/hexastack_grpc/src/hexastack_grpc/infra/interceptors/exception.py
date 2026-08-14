from collections.abc import Callable
from typing import Any

import grpc

from hexastack_core.domain.exceptions import HexastackError


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


class ExceptionServerInterceptor(grpc.ServerInterceptor):
    """Synchronous gRPC Server Interceptor mapping domain exceptions to gRPC status codes.

    Notes/Architectural Intent:
        Intercepts unhandled HexastackError domain exceptions and aborts the RPC
        call with appropriate native gRPC StatusCodes (NOT_FOUND, INVALID_ARGUMENT, etc.).
    """

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        handler: Any = continuation(handler_call_details)
        if handler is None:
            return handler

        unary_fn = getattr(handler, "unary_unary", None)
        if unary_fn is not None:

            def unary_wrapper(request: Any, context: grpc.ServicerContext) -> Any:
                try:
                    return unary_fn(request, context)
                except Exception as exc:  # noqa: BLE001
                    status_code, details = _map_exception_to_status_code(exc)
                    context.abort(status_code, details)

            return grpc.unary_unary_rpc_method_handler(
                unary_wrapper,
                request_deserializer=getattr(handler, "request_deserializer", None),
                response_serializer=getattr(handler, "response_serializer", None),
            )

        return handler


class AsyncExceptionServerInterceptor(grpc.aio.ServerInterceptor):
    """Asynchronous gRPC Server Interceptor mapping domain exceptions to gRPC status codes."""

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        handler: Any = await continuation(handler_call_details)
        if handler is None:
            return handler

        unary_fn = getattr(handler, "unary_unary", None)
        if unary_fn is not None:

            async def async_unary_wrapper(
                request: Any, context: grpc.aio.ServicerContext
            ) -> Any:
                try:
                    return await unary_fn(request, context)
                except Exception as exc:  # noqa: BLE001
                    status_code, details = _map_exception_to_status_code(exc)
                    await context.abort(status_code, details)

            return grpc.unary_unary_rpc_method_handler(
                async_unary_wrapper,
                request_deserializer=getattr(handler, "request_deserializer", None),
                response_serializer=getattr(handler, "response_serializer", None),
            )

        return handler


__all__ = [
    "AsyncExceptionServerInterceptor",
    "ExceptionServerInterceptor",
]
