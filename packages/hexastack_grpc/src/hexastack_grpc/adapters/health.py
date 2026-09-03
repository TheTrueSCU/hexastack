"""gRPC Standard Health Checking Protocol Servicer Adapter."""

from __future__ import annotations

from typing import Any

from grpc_health.v1 import health, health_pb2, health_pb2_grpc


class GrpcHealthServicer(health_pb2_grpc.HealthServicer):
    """Standard gRPC Health Checking Protocol implementation (grpc.health.v1.Health).

    Notes/Architectural Intent:
        Implements standard Kubernetes and service mesh gRPC liveness and readiness
        health probes (Check and Watch RPCs).
    """

    def __init__(self) -> None:
        """Initialize health servicer with standard grpc_health servicer."""
        self._servicer = health.HealthServicer()

    def set_serving_status(
        self,
        service: str,
        status: health_pb2.HealthCheckResponse.ServingStatus,
    ) -> None:
        """Set serving status for a specific service name or empty string for overall server.

        Args:
            service: Service name string (e.g. '', 'UserService').
            status: ServingStatus enum value (e.g. SERVING, NOT_SERVING).
        """
        self._servicer.set(service, status)

    def set_serving(self, service: str = "") -> None:
        """Mark service or overall server as SERVING."""
        self.set_serving_status(
            service,
            health_pb2.HealthCheckResponse.ServingStatus.SERVING,
        )

    def set_not_serving(self, service: str = "") -> None:
        """Mark service or overall server as NOT_SERVING."""
        self.set_serving_status(
            service,
            health_pb2.HealthCheckResponse.ServingStatus.NOT_SERVING,
        )

    def Check(self, request: Any, context: Any) -> Any:
        """Synchronous unary Check RPC delegator."""
        return self._servicer.Check(request, context)

    def Watch(self, request: Any, context: Any) -> Any:
        """Server-streaming Watch RPC delegator."""
        return self._servicer.Watch(request, context)

    def add_to_server(self, server: Any) -> None:
        """Attach health servicer to gRPC server instance."""
        health_pb2_grpc.add_HealthServicer_to_server(self._servicer, server)


__all__ = [
    "GrpcHealthServicer",
]
