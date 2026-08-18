"""Generic base classes for synchronous and asynchronous gRPC server interceptors.

Notes/Architectural Intent:
    Eliminates the repeated handler-resolution, guard, unary extraction, and
    method-handler rebuild boilerplate that is identical across every concrete
    interceptor (correlation, exception, logging, timing, etc.).

    Subclasses implement a single abstract method:
    - ``_handle_unary`` (sync) or ``_handle_unary_async`` (async)

    The base class owns the gRPC plumbing; the subclass owns only its
    cross-cutting concern.

    Supports ``grpc.ServerInterceptor`` (synchronous) and
    ``grpc.aio.ServerInterceptor`` (asynchronous) via two separate hierarchies
    so that typing remains strict and no coroutine/non-coroutine mixing occurs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import grpc


class GenericServerInterceptor(grpc.ServerInterceptor, ABC):
    """Abstract base for synchronous unary-unary gRPC server interceptors.

    Notes/Architectural Intent:
        Owns the repetitive handler-resolution and ``unary_unary`` extraction
        pattern so concrete subclasses implement only their own cross-cutting
        concern inside ``_handle_unary``.

        The base transparently passes through handlers for non-unary RPC types
        (client-streaming, server-streaming, bidi-streaming) so subclasses do
        not need to handle those cases unless they wish to.
    """

    @abstractmethod
    def _handle_unary(
        self,
        request: Any,
        context: grpc.ServicerContext,
        unary_fn: Callable[[Any, grpc.ServicerContext], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Execute the cross-cutting concern around the unary handler invocation.

        Args:
            request: The deserialized gRPC request message.
            context: The active ``grpc.ServicerContext`` for this RPC call.
            unary_fn: The next-in-chain unary handler callable to invoke.
            handler_call_details: Metadata about the incoming RPC call, including
                method name and invocation metadata.

        Returns:
            The response returned by ``unary_fn`` (or a substitute value).

        Raises:
            Exception: Subclasses may raise, suppress, or re-raise as needed.

        Notes/Architectural Intent:
            Subclasses must call ``unary_fn(request, context)`` to propagate the
            call downstream.  They may wrap the call in try/except, prepend or
            postpend logic, or modify context (e.g. abort) before/after.
        """
        ...

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercept handler resolution, wrapping unary-unary calls.

        Args:
            continuation: Callable that resolves the next handler in the chain.
            handler_call_details: Metadata about the incoming RPC call.

        Returns:
            A (possibly wrapped) ``grpc.RpcMethodHandler``.
        """
        handler: Any = continuation(handler_call_details)
        if handler is None:
            return handler

        unary_fn = getattr(handler, "unary_unary", None)
        if unary_fn is None:
            return handler

        interceptor = self

        def _wrapped(request: Any, context: grpc.ServicerContext) -> Any:
            return interceptor._handle_unary(
                request, context, unary_fn, handler_call_details
            )

        return grpc.unary_unary_rpc_method_handler(
            _wrapped,
            request_deserializer=getattr(handler, "request_deserializer", None),
            response_serializer=getattr(handler, "response_serializer", None),
        )


class AsyncGenericServerInterceptor(grpc.aio.ServerInterceptor, ABC):
    """Abstract base for asynchronous unary-unary gRPC server interceptors.

    Notes/Architectural Intent:
        Async counterpart to ``GenericServerInterceptor``. Owns the
        ``await continuation(...)`` / ``await context.abort(...)`` plumbing so
        concrete subclasses only implement ``_handle_unary_async``.
    """

    @abstractmethod
    async def _handle_unary_async(
        self,
        request: Any,
        context: grpc.aio.ServicerContext,
        unary_fn: Callable[[Any, grpc.aio.ServicerContext], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Execute the cross-cutting concern around the async unary handler invocation.

        Args:
            request: The deserialized gRPC request message.
            context: The active ``grpc.aio.ServicerContext`` for this RPC call.
            unary_fn: The next-in-chain async unary handler coroutine to invoke.
            handler_call_details: Metadata about the incoming RPC call, including
                method name and invocation metadata.

        Returns:
            The response returned by ``await unary_fn(request, context)``.

        Raises:
            Exception: Subclasses may raise, suppress, or re-raise as needed.
        """
        ...

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Intercept async handler resolution, wrapping unary-unary calls.

        Args:
            continuation: Async callable that resolves the next handler.
            handler_call_details: Metadata about the incoming RPC call.

        Returns:
            A (possibly wrapped) RPC method handler.
        """
        handler: Any = await continuation(handler_call_details)
        if handler is None:
            return handler

        unary_fn = getattr(handler, "unary_unary", None)
        if unary_fn is None:
            return handler

        interceptor = self

        async def _wrapped(request: Any, context: grpc.aio.ServicerContext) -> Any:
            return await interceptor._handle_unary_async(
                request, context, unary_fn, handler_call_details
            )

        return grpc.unary_unary_rpc_method_handler(
            _wrapped,
            request_deserializer=getattr(handler, "request_deserializer", None),
            response_serializer=getattr(handler, "response_serializer", None),
        )


__all__ = [
    "AsyncGenericServerInterceptor",
    "GenericServerInterceptor",
]
