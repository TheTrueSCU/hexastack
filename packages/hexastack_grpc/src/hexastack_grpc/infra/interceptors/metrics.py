"""gRPC Server Interceptor for recording RPC rate and duration metrics."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import grpc

from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.ports.metrics import MetricsPort
from hexastack_grpc.infra.interceptors.generic import GenericServerInterceptor


class MetricsServerInterceptor(GenericServerInterceptor):
    """gRPC Server Interceptor tracking RPC call counts and handling durations.

    Notes/Architectural Intent:
        Intercepts incoming gRPC invocations across unary and streaming handlers,
        measuring handling latency and recording status codes against MetricsPort.
        Guarded dynamically via FeatureFlagPort.
    """

    def __init__(
        self,
        metrics: MetricsPort | None = None,
        flags: FeatureFlagPort | None = None,
    ) -> None:
        """Initialize MetricsServerInterceptor.

        Args:
            metrics: Optional MetricsPort instance to record into.
            flags: Optional FeatureFlagPort to dynamically evaluate metrics emission.
        """
        self._metrics = metrics
        self._flags = flags

    def _handle_unary(
        self,
        request: Any,
        context: grpc.ServicerContext,
        unary_fn: Callable[[Any, grpc.ServicerContext], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """Measure and record RPC metrics around unary execution."""
        if self._metrics is None:
            return unary_fn(request, context)

        if self._flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not self._flags.is_enabled(
                "features.metrics.grpc", default=True, context=eval_ctx
            ):
                return unary_fn(request, context)

        method_name = handler_call_details.method or "/unknown/unknown"
        parts = method_name.strip("/").split("/")
        service = parts[0] if parts else "unknown"
        method = parts[1] if len(parts) > 1 else "unknown"

        start_time = time.perf_counter()
        status_code = "OK"
        try:
            return unary_fn(request, context)
        except Exception:
            status_code = "ERROR"
            raise
        finally:
            duration = time.perf_counter() - start_time
            self._metrics.increment_counter(
                "grpc_server_handled_total",
                value=1.0,
                labels={
                    "grpc_service": service,
                    "grpc_method": method,
                    "grpc_code": status_code,
                },
                description="Total gRPC RPCs handled",
            )
            self._metrics.record_histogram(
                "grpc_server_handling_seconds",
                value=duration,
                labels={"grpc_service": service, "grpc_method": method},
                description="gRPC server handling duration distribution in seconds",
            )


__all__ = [
    "MetricsServerInterceptor",
]
