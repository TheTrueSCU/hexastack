from collections.abc import Callable
from typing import Any

import grpc
from hexastack_core.utils.context import (
    correlation_id_ctx,
    new_correlation_id,
    set_correlation_id,
)

_CORRELATION_METADATA_KEY = "x-correlation-id"


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

        def extract_cid() -> str:
            if handler_call_details.invocation_metadata:
                for key, val in handler_call_details.invocation_metadata:
                    if key.lower() == _CORRELATION_METADATA_KEY:
                        return (
                            val.decode("utf-8") if isinstance(val, bytes) else str(val)
                        )
            return new_correlation_id()

        unary_fn = getattr(handler, "unary_unary", None)
        if unary_fn is not None:

            def unary_wrapper(request: Any, context: grpc.ServicerContext) -> Any:
                cid = extract_cid()
                token = set_correlation_id(cid)
                try:
                    return unary_fn(request, context)
                finally:
                    correlation_id_ctx.reset(token)

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

        def extract_cid() -> str:
            if handler_call_details.invocation_metadata:
                for key, val in handler_call_details.invocation_metadata:
                    if key.lower() == _CORRELATION_METADATA_KEY:
                        return (
                            val.decode("utf-8") if isinstance(val, bytes) else str(val)
                        )
            return new_correlation_id()

        unary_fn = getattr(handler, "unary_unary", None)
        if unary_fn is not None:

            async def async_unary_wrapper(
                request: Any, context: grpc.aio.ServicerContext
            ) -> Any:
                cid = extract_cid()
                token = set_correlation_id(cid)
                try:
                    return await unary_fn(request, context)
                finally:
                    correlation_id_ctx.reset(token)

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
