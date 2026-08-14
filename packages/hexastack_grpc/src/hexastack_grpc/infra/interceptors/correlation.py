from collections.abc import Callable
from typing import Any

import grpc

from hexastack_core.utils.context import (
    correlation_scope,
    new_correlation_id,
)
from hexastack_grpc.infra.interceptors.generic import (
    AsyncGenericServerInterceptor,
    GenericServerInterceptor,
)

_CORRELATION_METADATA_KEY = "x-correlation-id"


def _extract_cid(metadata: Any) -> str:
    """Extract correlation ID from gRPC invocation metadata or generate fresh UUID."""
    if metadata:
        for key, val in metadata:
            if key.lower() == _CORRELATION_METADATA_KEY:
                return val.decode("utf-8") if isinstance(val, bytes) else str(val)
    return new_correlation_id()


class CorrelationServerInterceptor(GenericServerInterceptor):
    """Synchronous gRPC Server Interceptor for correlation ID propagation.

    Notes/Architectural Intent:
        Extracts 'x-correlation-id' from incoming gRPC invocation metadata,
        or generates a fresh UUID4, setting it in ContextVar for the RPC duration.
    """

    def _handle_unary(
        self,
        request: Any,
        context: grpc.ServicerContext,
        unary_fn: Callable[[Any, grpc.ServicerContext], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Attach a correlation scope for the duration of the unary RPC call."""
        cid = _extract_cid(handler_call_details.invocation_metadata)
        with correlation_scope(cid):
            return unary_fn(request, context)


class AsyncCorrelationServerInterceptor(AsyncGenericServerInterceptor):
    """Asynchronous gRPC Server Interceptor for correlation ID propagation."""

    async def _handle_unary_async(
        self,
        request: Any,
        context: grpc.aio.ServicerContext,
        unary_fn: Callable[[Any, grpc.aio.ServicerContext], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Attach a correlation scope for the duration of the async unary RPC call."""
        cid = _extract_cid(handler_call_details.invocation_metadata)
        with correlation_scope(cid):
            return await unary_fn(request, context)


__all__ = [
    "AsyncCorrelationServerInterceptor",
    "CorrelationServerInterceptor",
]
