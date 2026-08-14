import logging
import time
from collections.abc import Callable
from typing import Any

import grpc

from hexastack_grpc.infra.interceptors.generic import GenericServerInterceptor

logger = logging.getLogger("hexastack.grpc")


class LoggingServerInterceptor(GenericServerInterceptor):
    """Synchronous gRPC Server Interceptor for structured RPC logging.

    Notes/Architectural Intent:
        Logs incoming RPC method calls and completion statuses, capturing exceptions
        and logging structured error details.
    """

    def _handle_unary(
        self,
        request: Any,
        context: grpc.ServicerContext,
        unary_fn: Callable[[Any, grpc.ServicerContext], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Log the RPC call start, completion, and any errors."""
        method = handler_call_details.method
        logger.info("Handling gRPC call: %s", method)
        try:
            res = unary_fn(request, context)
            logger.info("Completed gRPC call: %s", method)
            return res
        except Exception as e:
            logger.error("Failed gRPC call %s: %s", method, e)
            raise


class TimingServerInterceptor(GenericServerInterceptor):
    """Synchronous gRPC Server Interceptor for measuring RPC execution latency."""

    def _handle_unary(
        self,
        request: Any,
        context: grpc.ServicerContext,
        unary_fn: Callable[[Any, grpc.ServicerContext], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Measure and log the elapsed time of the unary RPC call."""
        method = handler_call_details.method
        start = time.perf_counter()
        try:
            return unary_fn(request, context)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.debug("RPC %s executed in %.2fms", method, duration_ms)


__all__ = [
    "LoggingServerInterceptor",
    "TimingServerInterceptor",
]
