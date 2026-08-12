import logging
import time
from collections.abc import Callable
from typing import Any

import grpc

logger = logging.getLogger("hexastack.grpc")


class LoggingServerInterceptor(grpc.ServerInterceptor):
    """Synchronous gRPC Server Interceptor for structured RPC logging.

    Notes/Architectural Intent:
        Logs incoming RPC method calls and completion statuses, capturing exceptions
        and logging structured error details.
    """

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        handler: Any = continuation(handler_call_details)
        if handler is None:
            return handler

        method = handler_call_details.method
        unary_fn = getattr(handler, "unary_unary", None)

        if unary_fn is not None:

            def unary_wrapper(request: Any, context: grpc.ServicerContext) -> Any:
                logger.info("Handling gRPC call: %s", method)
                try:
                    res = unary_fn(request, context)
                    logger.info("Completed gRPC call: %s", method)
                    return res
                except Exception as e:
                    logger.error("Failed gRPC call %s: %s", method, e)
                    raise

            return grpc.unary_unary_rpc_method_handler(
                unary_wrapper,
                request_deserializer=getattr(handler, "request_deserializer", None),
                response_serializer=getattr(handler, "response_serializer", None),
            )

        return handler


class TimingServerInterceptor(grpc.ServerInterceptor):
    """Synchronous gRPC Server Interceptor for measuring RPC execution latency."""

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        handler: Any = continuation(handler_call_details)
        if handler is None:
            return handler

        method = handler_call_details.method
        unary_fn = getattr(handler, "unary_unary", None)

        if unary_fn is not None:

            def unary_wrapper(request: Any, context: grpc.ServicerContext) -> Any:
                start = time.perf_counter()
                try:
                    return unary_fn(request, context)
                finally:
                    duration_ms = (time.perf_counter() - start) * 1000
                    logger.debug("RPC %s executed in %.2fms", method, duration_ms)

            return grpc.unary_unary_rpc_method_handler(
                unary_wrapper,
                request_deserializer=getattr(handler, "request_deserializer", None),
                response_serializer=getattr(handler, "response_serializer", None),
            )

        return handler


__all__ = [
    "LoggingServerInterceptor",
    "TimingServerInterceptor",
]
