from collections.abc import Callable
from typing import Any

import grpc
from hexastack_core.utils.context import (
    correlation_scope,
    new_correlation_id,
)

_CORRELATION_METADATA_KEY = "x-correlation-id"


def _extract_cid(metadata: Any) -> str:
    """Extract correlation ID from gRPC invocation metadata or generate fresh UUID."""
    if metadata:
        for key, val in metadata:
            if key.lower() == _CORRELATION_METADATA_KEY:
                return val.decode("utf-8") if isinstance(val, bytes) else str(val)
    return new_correlation_id()


class CorrelationServerInterceptor(grpc.ServerInterceptor):
    """Synchronous gRPC Server Interceptor for correlation ID propagation.

    Notes/Architectural Intent:
        Extracts 'x-correlation-id' from incoming gRPC invocation metadata,
        or generates a fresh UUID4, setting it in ContextVar for the RPC duration.
    """

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercept RPC handler resolution to attach correlation scope."""
        handler: Any = continuation(handler_call_details)
        if handler is None:
            return handler

        unary_fn = getattr(handler, "unary_unary", None)
        if unary_fn is not None:

            def unary_wrapper(request: Any, context: grpc.ServicerContext) -> Any:
                cid = _extract_cid(handler_call_details.invocation_metadata)
                with correlation_scope(cid):
                    return unary_fn(request, context)

            return grpc.unary_unary_rpc_method_handler(
                unary_wrapper,
                request_deserializer=getattr(handler, "request_deserializer", None),
                response_serializer=getattr(handler, "response_serializer", None),
            )

        return handler


class AsyncCorrelationServerInterceptor(grpc.aio.ServerInterceptor):
    """Asynchronous gRPC Server Interceptor for correlation ID propagation."""

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Intercept async RPC handler resolution."""
        handler: Any = await continuation(handler_call_details)
        if handler is None:
            return handler

        unary_fn = getattr(handler, "unary_unary", None)
        if unary_fn is not None:

            async def async_unary_wrapper(
                request: Any, context: grpc.aio.ServicerContext
            ) -> Any:
                cid = _extract_cid(handler_call_details.invocation_metadata)
                with correlation_scope(cid):
                    return await unary_fn(request, context)

            return grpc.unary_unary_rpc_method_handler(
                async_unary_wrapper,
                request_deserializer=getattr(handler, "request_deserializer", None),
                response_serializer=getattr(handler, "response_serializer", None),
            )

        return handler


__all__ = [
    "AsyncCorrelationServerInterceptor",
    "CorrelationServerInterceptor",
]
